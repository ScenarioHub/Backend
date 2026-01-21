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