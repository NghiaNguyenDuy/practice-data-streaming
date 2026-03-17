-- ADD
INSERT INTO bde_module3_lesson4.visits_new VALUES
('visit3', 1, 'home.html', NOW() + '1 second', 'smartphone', 'iOS 11'),
  ('visit3', 1, 'articles.html', NOW() + '2 seconds', 'smartphone', 'iOS 11'),
  ('visit3', 1, 'contact.html', NOW() + '3 seconds', 'smartphone', 'iOS 11'),

('visit4', 2, 'home.html', NOW() + '2 seconds', 'smartphone', 'Android 9.0'),
  ('visit4', 2, 'about.html', NOW()+ '3 seconds', 'smartphone', 'Android 9.0'),
  ('visit4', 2, 'contact.html', NOW()+ '4 seconds', 'smartphone', 'Android 9.0'),

('visit5', 2, 'home.html', NOW()+ '2 seconds', 'tablet', 'Android 9.0'),
  ('visit5', 2, 'about.html', NOW()+ '3 seconds', 'tablet', 'Android 9.0'),
  ('visit5', 2, 'contact.html', NOW()+ '4 seconds', 'tablet', 'Android 9.0');
  
  
  
-- UPDATE
UPDATE bde_module3_lesson4.visits_new SET device_type = 'pc' WHERE visit_id = 'visit3';
 
-- DELETE
DELETE FROM bde_module3_lesson4.visits_new WHERE visit_id = 'visit3';
