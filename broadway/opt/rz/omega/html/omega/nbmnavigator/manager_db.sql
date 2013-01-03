drop DATABASE IF EXISTS `manager_db`;
create schema manager_db;

use manager_db;

CREATE TABLE `DeletedEntityModel` (
  `name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `managerName` varchar(100),
  `url` varchar(255) DEFAULT NULL,
  `deletedOn` datetime DEFAULT NULL
);


CREATE TABLE `EntityModel` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `managerName` varchar(100),
  `url` varchar(255) DEFAULT NULL,
  `parentId` int(11) DEFAULT NULL,
  `lft` int(11) NOT NULL,
  `rgt` int(11) NOT NULL,
  `createdOn` timestamp NULL DEFAULT NULL,
  `type` varchar(20) DEFAULT NULL,
  `nodeId` varchar(45) NOT NULL,
  `pointKey` varchar(150) DEFAULT NULL,
  `displayURL` varchar(255) DEFAULT NULL,
  `label` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_EntityModel` (`parentId`),
  KEY `INX_ARMS` (`lft`,`rgt`,`name`,`description`,`managerName`),
  KEY `INX_URL` (`url`),
  KEY `INX_NAME` (`name`),
  KEY `INX_NAME_URL` (`name`, `url`)
);




CREATE TABLE `IdentityGenerator` (
  `sequence_name` varchar(30) NOT NULL,
  `next_hi_value` int(11) DEFAULT NULL,
  PRIMARY KEY (`sequence_name`)
);



CREATE TABLE `StagingEntityModel` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `managerName` varchar(100),
  `url` varchar(255) DEFAULT NULL,
  `parentId` bigint(11) DEFAULT NULL,
  `lft` int(11) NOT NULL,
  `rgt` int(11) NOT NULL,
  `createdOn` timestamp NULL DEFAULT NULL,
  `type` varchar(20) DEFAULT NULL,
  `nodeId` varchar(45) NOT NULL,
  `pointKey` varchar(150) DEFAULT NULL,
  `displayURL` varchar(255) DEFAULT NULL,
  `label` varchar(45) DEFAULT NULL,
  KEY `INX_URL` (`url`)
) ;


INSERT INTO `manager_db`.`IdentityGenerator`
    (`sequence_name`, `next_hi_value`)
VALUES
    ("EntityModel", 0 );


CREATE TABLE `pointKey` (
  `id` int(11) NOT NULL,
  `pointKey` varchar(45) NOT NULL,
  `description` varchar(200) NOT NULL,
  PRIMARY KEY (`id`)
);




INSERT INTO `manager_db`.`pointKey` VALUES(1	, 'VavDmpr', 'VAV Damper');
INSERT INTO `manager_db`.`pointKey` VALUES(2	, 'SaTemp', 'Supply Air Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(3	, 'HcVlvCtrl', 'Heating Coil Valve Control');
INSERT INTO `manager_db`.`pointKey` VALUES(4	, 'RadVlvCtrl', 'Radiator Valve Control');
INSERT INTO `manager_db`.`pointKey` VALUES(5	, 'Saflo', 'Supply Air Flow');
INSERT INTO `manager_db`.`pointKey` VALUES(6	, 'RmTemp', 'Room Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(7	, 'HtgStg1', 'Heating Stage 1');
INSERT INTO `manager_db`.`pointKey` VALUES(8	, 'HtgStg2', 'Heating Stage 2');
INSERT INTO `manager_db`.`pointKey` VALUES(9	, 'HtgStg3', 'Heating Stage 3');
INSERT INTO `manager_db`.`pointKey` VALUES(10	, 'HtgStg4', 'Heating Stage 4');
INSERT INTO `manager_db`.`pointKey` VALUES(11	, 'RadStg1', 'Radiator  Stage 1');
INSERT INTO `manager_db`.`pointKey` VALUES(12	, 'RadStg2', 'Radiator  Stage 2');
INSERT INTO `manager_db`.`pointKey` VALUES(13	, 'SaFanEn', 'Supply Fan Output Enable ');
INSERT INTO `manager_db`.`pointKey` VALUES(14	, 'SaFanSts', 'Supply Fan Status ');
INSERT INTO `manager_db`.`pointKey` VALUES(15	, 'SaRH', 'Suppy Air RH');
INSERT INTO `manager_db`.`pointKey` VALUES(16	, 'OccHtgSP', 'Occupied Heating Setpoint');
INSERT INTO `manager_db`.`pointKey` VALUES(17	, 'UnOccHtgSP', 'Unoccupied Heating Setpoint');
INSERT INTO `manager_db`.`pointKey` VALUES(18	, 'OccClgSP', 'Occupied Cooling Setpoint');
INSERT INTO `manager_db`.`pointKey` VALUES(19	, 'UnOccClgSP', 'Unoccupied Cooling Setpoint');
INSERT INTO `manager_db`.`pointKey` VALUES(20	, 'EffSP', 'Effective Setpoint');
INSERT INTO `manager_db`.`pointKey` VALUES(21	, 'MaDmpr', 'Mixed Air Damper');
INSERT INTO `manager_db`.`pointKey` VALUES(22	, 'MaTemp', 'Mixed Air Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(23	, 'FltAlm', 'Differential Pressure Switch for Filter Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(24	, 'CclVlcVtrl', 'Cooling Coil Valve Control');
INSERT INTO `manager_db`.`pointKey` VALUES(25	, 'Dx1En', 'Cooling Stage 1');
INSERT INTO `manager_db`.`pointKey` VALUES(26	, 'Dx2En', 'Cooling Stage 2');
INSERT INTO `manager_db`.`pointKey` VALUES(27	, 'Dx3En', 'Cooling Stage 3');
INSERT INTO `manager_db`.`pointKey` VALUES(28	, 'Dx4En', 'Cooling Stage 4');
INSERT INTO `manager_db`.`pointKey` VALUES(29	, 'RaCO2', 'Return Air CO2');
INSERT INTO `manager_db`.`pointKey` VALUES(30	, 'ClgHtgVlv', 'Cooling/Heating Valve Control in FCU 2 Pipe System');
INSERT INTO `manager_db`.`pointKey` VALUES(31	, 'ChgOvrFb', 'Change Over feedback for Cooling Heating  in FCU 2 Pipe System');
INSERT INTO `manager_db`.`pointKey` VALUES(32	, 'Comp1En', 'Compressor 1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(33	, 'Comp2En', 'Compressor 2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(34	, 'ChgOvr', 'Change Over for Heat Pump');
INSERT INTO `manager_db`.`pointKey` VALUES(35	, 'AuxHtg', 'Auxillary Heating');
INSERT INTO `manager_db`.`pointKey` VALUES(36	, 'CoolEn', 'Cool Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(37	, 'HeatEn', 'Heat Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(38	, 'RaTemp', 'Return Air Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(39	, 'RmRH', 'Room RH');
INSERT INTO `manager_db`.`pointKey` VALUES(40	, 'RaFanEn', 'Return  Fan Output Enable ');
INSERT INTO `manager_db`.`pointKey` VALUES(41	, 'RaFanSts', 'Return Fan Status ');
INSERT INTO `manager_db`.`pointKey` VALUES(42	, 'SaSmkAlm', 'Supply Air Smoke Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(43	, 'RaSmkAlm', 'Return Air Smoke Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(44	, 'RaRH', 'Return Air RH');
INSERT INTO `manager_db`.`pointKey` VALUES(45	, 'EaFanEn', 'Exhaust  Fan Output Enable ');
INSERT INTO `manager_db`.`pointKey` VALUES(46	, 'EaFanSts', 'Exhaust Fan Status ');
INSERT INTO `manager_db`.`pointKey` VALUES(47	, 'HtRcvWhlOut', 'Heat Recovery Wheel Output En');
INSERT INTO `manager_db`.`pointKey` VALUES(48	, 'HtRcvWhlSts', 'Heat Recovery Wheel Status');
INSERT INTO `manager_db`.`pointKey` VALUES(49	, 'HtRcvWhlCtrl', 'Heat Recovery Wheel Control');
INSERT INTO `manager_db`.`pointKey` VALUES(50	, 'HtRcvByPDmprCtl', 'Heat Recovery Wheel Bypass Damper Control');
INSERT INTO `manager_db`.`pointKey` VALUES(51	, 'SaStaticPr', 'Supply Air Static Pressure');
INSERT INTO `manager_db`.`pointKey` VALUES(52	, 'SaFanSpdCtrl', 'Supply Air Fan Speed Control');
INSERT INTO `manager_db`.`pointKey` VALUES(53	, 'Bo1En', 'Boiler 1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(54	, 'Bo1Sts', 'Boiler 1 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(55	, 'Bo2En', 'Boiler 2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(56	, 'Bo2Sts', 'Boiler 2 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(57	, 'Pmp1En', 'Pump 1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(58	, 'Pmp1Sts', 'Pump 1 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(59	, 'Pmp2En', 'Pump 2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(60	, 'Pmp2Sts', 'Pump 2 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(61	, 'HwSTemp', 'Hot Water Supply Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(62	, 'HwRTemp', 'Hot Water Return Temperautre');
INSERT INTO `manager_db`.`pointKey` VALUES(63	, 'OATemp', 'Outside Air Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(64	, 'Bo1LoFire', 'Boiler 1 Low Fire');
INSERT INTO `manager_db`.`pointKey` VALUES(65	, 'Bo1HiFire', 'Boiler 1 High Fire');
INSERT INTO `manager_db`.`pointKey` VALUES(66	, 'Bo1InTemp', 'Boiler 1 Inlet Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(67	, 'Bo1OutTemp', 'Boiler 1 Outlet Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(68	, 'Bo1CPmp', 'Boiler 1 Circulating Pump');
INSERT INTO `manager_db`.`pointKey` VALUES(69	, 'Bo1CPmpSts', 'Boiler 1 Circulating Pump Status');
INSERT INTO `manager_db`.`pointKey` VALUES(70	, 'HwDP', 'Hot Water Differential Pressure');
INSERT INTO `manager_db`.`pointKey` VALUES(71	, 'Bo2LoFire', 'Boiler 2 Low Fire');
INSERT INTO `manager_db`.`pointKey` VALUES(72	, 'Bo2HiFire', 'Boiler 2 High Fire');
INSERT INTO `manager_db`.`pointKey` VALUES(73	, 'Bo2InTemp', 'Boiler 2 Inlet Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(74	, 'Bo2OutTemp', 'Boiler 2 Outlet Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(75	, 'Bo2CPmp', 'Boiler 2 Circulating Pump');
INSERT INTO `manager_db`.`pointKey` VALUES(76	, 'Bo2CPmpSts', 'Boiler 2 Circulating Pump Status');
INSERT INTO `manager_db`.`pointKey` VALUES(77	, 'CH1Ctrl', 'Chiller 1 Control');
INSERT INTO `manager_db`.`pointKey` VALUES(78	, 'CH1En', 'Chiller 1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(79	, 'CH1sts', 'Chiller 1 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(80	, 'CH1CntAlm', 'Chiller 1 Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(81	, 'CHWSpTmp', 'Chilled Water Supply Temp');
INSERT INTO `manager_db`.`pointKey` VALUES(82	, 'CHWRTmp', 'Chilled Water Return Temp');
INSERT INTO `manager_db`.`pointKey` VALUES(83	, 'CHWPmp1En', 'Chillled Water Pump1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(84	, 'CHWPmp1Sts', 'Chilled Water Pump1 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(85	, 'CHWPmp2En', 'Chilled Water Pump2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(86	, 'CHWPmp2Sts', 'Chilled Water Pump2 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(87	, 'CH2Ctrl', 'Chiller 2 Control');
INSERT INTO `manager_db`.`pointKey` VALUES(88	, 'CH2En', 'Chiller 2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(89	, 'CH2sts', 'Chiller 2 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(90	, 'CH2CntAlm', 'Chiller 2 Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(91	, 'CNDPMP1En', 'Condenser Water Pump1 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(92	, 'CNDPMP1Sts', 'Condenser Water Pump1 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(93	, 'CNDPMP2En', 'Condenser Water Pump2 Enable');
INSERT INTO `manager_db`.`pointKey` VALUES(94	, 'CNDPMP2Sts', 'Condenser Water Pump2 Status');
INSERT INTO `manager_db`.`pointKey` VALUES(95	, 'CNWSpTmp', 'Condenser Water Supply Temperature');
INSERT INTO `manager_db`.`pointKey` VALUES(96	, 'CNWRTmp', 'Condenser Water ReturnTemperature');
INSERT INTO `manager_db`.`pointKey` VALUES(97	, 'CT1HILWAlm', 'Cooling Tower Hi Limit Water Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(98	, 'CT1LOLWAlm', 'Cooling Tower Lo Limit Water Alarm');
INSERT INTO `manager_db`.`pointKey` VALUES(99	, 'CT1FanLo', 'Cooling Tower Fan Lo speed Output');
INSERT INTO `manager_db`.`pointKey` VALUES(100	, 'CT1FanHi', 'Cooling Tower Fan Hi speed Output');
INSERT INTO `manager_db`.`pointKey` VALUES(101	, 'LightON_OFF', 'Light ON/OFF');
INSERT INTO `manager_db`.`pointKey` VALUES(102	, 'Lux', 'Ambience Lux');
INSERT INTO `manager_db`.`pointKey` VALUES(103	, 'Occupancy', 'Occupancy detection');
INSERT INTO `manager_db`.`pointKey` VALUES(104	, 'LightSts', 'Light Status');
INSERT INTO `manager_db`.`pointKey` VALUES(105	, 'Lightlvl', 'Light Control Level');

