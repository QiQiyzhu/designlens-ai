-- SQLite. Bind :is_demo (0 or 1) and UTC ISO8601 :since_day / :since_week.
-- DEMO activity is never user acquisition, retention or product impact.

-- DAU / WAU; distinct identity, not event count.
SELECT COUNT(DISTINCT CASE WHEN timestamp >= :since_day THEN user_id END) AS dau,
       COUNT(DISTINCT CASE WHEN timestamp >= :since_week THEN user_id END) AS wau
FROM events WHERE is_demo = :is_demo;

-- Ordered project funnel; later events are joined only after the prior stage.
WITH p AS (
 SELECT project_id, MIN(timestamp) AS t FROM events WHERE name='project_created' AND is_demo=:is_demo GROUP BY project_id
), s AS (
 SELECT p.project_id, MIN(e.timestamp) AS t FROM p JOIN events e ON e.project_id=p.project_id AND e.timestamp>=p.t
 WHERE e.name='source_uploaded' AND e.is_demo=:is_demo GROUP BY p.project_id
), i AS (
 SELECT s.project_id, MIN(e.timestamp) AS t FROM s JOIN events e ON e.project_id=s.project_id AND e.timestamp>=s.t
 WHERE e.name='insight_accepted' AND e.is_demo=:is_demo GROUP BY s.project_id
), o AS (
 SELECT i.project_id, MIN(e.timestamp) AS t FROM i JOIN events e ON e.project_id=i.project_id AND e.timestamp>=i.t
 WHERE e.name='opportunity_created' AND e.is_demo=:is_demo GROUP BY i.project_id
), x AS (
 SELECT o.project_id, MIN(e.timestamp) AS t FROM o JOIN events e ON e.project_id=o.project_id AND e.timestamp>=o.t
 WHERE e.name='experiment_created' AND e.is_demo=:is_demo GROUP BY o.project_id
)
SELECT 'project_created' AS stage, COUNT(*) AS projects FROM p UNION ALL
SELECT 'source_uploaded', COUNT(*) FROM s UNION ALL SELECT 'insight_accepted', COUNT(*) FROM i UNION ALL
SELECT 'opportunity_created', COUNT(*) FROM o UNION ALL SELECT 'experiment_created', COUNT(*) FROM x;

-- Current distinct insight state avoids repeated review clicks inflating acceptance.
SELECT SUM(json_extract(data,'$.status')='accepted') AS accepted,
       SUM(json_extract(data,'$.status')='rejected') AS rejected,
       1.0*SUM(json_extract(data,'$.status')='accepted') /
       NULLIF(SUM(json_extract(data,'$.status') IN ('accepted','rejected')),0) AS acceptance_rate
FROM entities WHERE kind='insights' AND json_extract(data,'$.is_demo')=:is_demo;

-- Pending human review is not terminal success.
SELECT COUNT(*) AS terminal_runs,
       1.0*SUM(status IN ('completed','abstained'))/NULLIF(COUNT(*),0) AS success_rate
FROM workflow_runs WHERE is_demo=:is_demo AND status IN ('completed','abstained','failed','rejected');

-- Feature adoption is distinct projects, with an explicit denominator.
SELECT name, COUNT(DISTINCT project_id) AS projects,
       1.0*COUNT(DISTINCT project_id)/(SELECT NULLIF(COUNT(DISTINCT project_id),0) FROM events WHERE is_demo=:is_demo) AS adoption
FROM events WHERE is_demo=:is_demo AND name IN ('source_uploaded','workflow_run','evaluation_run','experiment_created') GROUP BY name;

-- Activation: eligible project cohort has had a full 7-day opportunity to activate.
WITH cohort AS (
 SELECT project_id, MIN(timestamp) AS created FROM events WHERE name='project_created' AND is_demo=:is_demo GROUP BY project_id
), accepted AS (
 SELECT project_id, MIN(timestamp) AS accepted FROM events WHERE name='insight_accepted' AND is_demo=:is_demo GROUP BY project_id
)
SELECT COUNT(*) AS matured_projects,
       SUM(a.accepted>=c.created AND julianday(a.accepted)-julianday(c.created)<=7) AS activated
FROM cohort c LEFT JOIN accepted a USING(project_id) WHERE julianday('now')-julianday(c.created)>=7;

-- Week-4 retention: first accepted insight anchors activation, observe days 28–34.
WITH activated AS (
 SELECT user_id, MIN(timestamp) AS at FROM events WHERE name='insight_accepted' AND is_demo=:is_demo GROUP BY user_id
), mature AS (SELECT * FROM activated WHERE julianday('now')-julianday(at)>=35)
SELECT COUNT(*) AS eligible_users,
       SUM(EXISTS(SELECT 1 FROM events e WHERE e.user_id=m.user_id AND e.is_demo=:is_demo
           AND julianday(e.timestamp)-julianday(m.at)>=28 AND julianday(e.timestamp)-julianday(m.at)<35)) AS retained
FROM mature m;
