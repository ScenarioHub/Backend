USE scenariohub;

insert into users value(1, 'email', 'pass', 'name', 'nm', null, now(), now());
insert into scenarios value(1, 1, 'file', 'video', 'OpenSCENARIO', '1.2', 100, 'snippet', now());
insert into posts value(1, 1, 1, 'title', 'template description', 'description', 0, 0, 0, now());
insert into tags 
values	(1, '어린이', now()),
		(2, '보행자', now()),
		(3, '안전', now());
insert into scenario_tags 
values (1, 1), (1, 2);

insert into maps(map_name, description, file_url, img_url) value('crest-curve', null, '/home/scenariohub/ScenarioHub/data/xodr/crest-curve.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/crest-curve.png');
insert into maps(map_name, description, file_url, img_url) value('curve_r100', null, '/home/scenariohub/ScenarioHub/data/xodr/curve_r100.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/curve_r100.png');
insert into maps(map_name, description, file_url, img_url) value('curves_elevation', null, '/home/scenariohub/ScenarioHub/data/xodr/curves_elevation.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/curves_elevation.png');
insert into maps(map_name, description, file_url, img_url) value('e6mini-lht', null, '/home/scenariohub/ScenarioHub/data/xodr/e6mini-lht.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/e6mini-lht.png');
insert into maps(map_name, description, file_url, img_url) value('e6mini', null, '/home/scenariohub/ScenarioHub/data/xodr/e6mini.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/e6mini.png');
insert into maps(map_name, description, file_url, img_url) value('fabriksgatan', null, '/home/scenariohub/ScenarioHub/data/xodr/fabriksgatan.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/fabriksgatan.png');
insert into maps(map_name, description, file_url, img_url) value('jolengatan', null, '/home/scenariohub/ScenarioHub/data/xodr/jolengatan.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/jolengatan.png');
insert into maps(map_name, description, file_url, img_url) value('multi_intersections', null, '/home/scenariohub/ScenarioHub/data/xodr/multi_intersections.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/multi_intersections.png');
insert into maps(map_name, description, file_url, img_url) value('soderleden', null, '/home/scenariohub/ScenarioHub/data/xodr/soderleden.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/soderleden.png');
insert into maps(map_name, description, file_url, img_url) value('straight_500m', null, '/home/scenariohub/ScenarioHub/data/xodr/straight_500m.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/straight_500m.png');
insert into maps(map_name, description, file_url, img_url) value('straight_500m_signs', null, '/home/scenariohub/ScenarioHub/data/xodr/straight_500m_signs.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/straight_500m_signs.png');
insert into maps(map_name, description, file_url, img_url) value('tunnels', null, '/home/scenariohub/ScenarioHub/data/xodr/tunnels.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/tunnels.png');
insert into maps(map_name, description, file_url, img_url) value('two_plus_one', null, '/home/scenariohub/ScenarioHub/data/xodr/two_plus_one.xodr', '/home/scenariohub/ScenarioHub/data/xodr/previews/two_plus_one.png');
