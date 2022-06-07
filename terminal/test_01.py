"""
    小料对接接口封装
"""
import os
import re
import sys

import django
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mes.settings")
django.setup()

from django.db.transaction import atomic
from mes.settings import DATABASES
from terminal.models import WeightTankStatus


class JZTankStatusSync(object):
    equip_no_ip = {k: v.get("HOST", "10.4.23.79") for k, v in DATABASES.items()}

    def __init__(self, equip_no: str):
        self.url = f"http://{self.equip_no_ip.get(equip_no, '10.4.23.79')}:1997/CSharpWebService/Service.asmx"
        self.queryset = WeightTankStatus.objects.filter(equip_no=equip_no, use_flag=True)
        self.equip_no = equip_no

    @atomic
    def sync_jz(self, tank_no=None):
        # tank_no 3A 开3A罐门
        if tank_no:
            tank_int = int(tank_no[0]) * 2 - 1 if 'A' in tank_no else int(tank_no[0]) * 2
            send_data = f"""<?xml version="1.0" encoding="utf-16"?>
                                        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                                            <soap:Body>
                                                <SetRealData xmlns="http://www.realinfo.com.cn/">
                                                    <names>
                                                        <string>OPEN_DOOR_Bin.PV</string>
                                                        <string>OPEN_DOOR_Request.PV</string>
                                                    </names>
                                                    <datas>
                                                        <string>{tank_int}</string>
                                                        <string>1</string>
                                                    </datas>
                                                </SetRealData>
                                            </soap:Body>
                                        </soap:Envelope>"""
            open_info = requests.post(self.url, data=send_data.encode('utf-8'), timeout=5)
            res = open_info.content.decode('utf-8')
            result_flag = re.findall(r'<ns1:SetRealDataResult>(.*)</ns1:SetRealDataResult>', res)[0]
            if result_flag != 'true':
                raise ValueError(f'下发开门指令失败, 罐号: {tank_no}')
        point_name = [
            '1A_U1_0152_S1_DoorOFg.pv', '1A_U1_0153_S1_HLevelSFg.pv', '1A_U1_0154_S1_LLevelSFg.pv',
            'D2_0040_B1_Mname.desc',  # A1(1[关门], 0[高位没料], 1[低位有料]), '防老剂4020'
            '2A_U1_0272_S3_DoorOFg.pv', '2A_U1_0273_S3_HLevelSFg.pv', '2A_U1_0274_S3_LLevelSFg.pv',
            'D2_0120_B3_Mname.desc',  # A2
            '3A_U1_0392_S5_DoorOFg.pv', '3A_U1_0393_S5_HLevelSFg.pv', '3A_U1_0394_S5_LLevelSFg.pv',
            'D2_0200_B5_Mname.desc',  # A3
            '4A_U1_0512_S7_DoorOFg.pv', '4A_U1_0513_S7_HLevelSFg.pv', '4A_U1_0514_S7_LLevelSFg.pv',
            'D2_0280_B7_Mname.desc',  # A4
            '5A_U1_0632_S9_DoorOFg.pv', '5A_U1_0633_S9_HLevelSFg.pv', '5A_U1_0634_S9_LLevelSFg.pv',
            'D2_0360_B9_Mname.desc',  # A5
            '6A_U1_0752_S11_DoorOFg.pv', '6A_U1_0753_S11_HLevelSFg.pv', '6A_U1_0754_S11_LLevelSFg.pv',
            'D2_0440_B11_Mname.desc',  # A6
            '7A_U1_0872_S13_DoorOFg.pv', '7A_U1_0873_S13_HLevelSFg.pv', '7A_U1_0874_S13_LLevelSFg.pv',
            'D2_0520_B13_Mname.desc',  # 7A
            '8A_U1_0992_S15_DoorOFg.pv', '8A_U1_0993_S15_HLevelSFg.pv', '8A_U1_0994_S15_LLevelSFg.pv',
            'D2_0600_B15_Mname.desc',  # 8A
            '9A_U1_1112_S17_DoorOFg.pv', '9A_U1_1113_S17_HLevelSFg.pv', '9A_U1_1114_S17_LLevelSFg.pv',
            'D2_0680_B17_Mname.desc',  # 9A
            '1B_U1_0212_S2_DoorOFg.pv', '1B_U1_0213_S2_HLevelSFg.pv', '1B_U1_0214_S2_LLevelSFg.pv',
            'D2_0080_B2_Mname.desc',  # 1B
            '2B_U1_0332_S4_DoorOFg.pv', '2B_U1_0333_S4_HLevelSFg.pv', '2B_U1_0334_S4_LLevelSFg.pv',
            'D2_0160_B4_Mname.desc',  # 2B
            '3B_U1_0452_S6_DoorOFg.pv', '3B_U1_0453_S6_HLevelSFg.pv', '3B_U1_0454_S6_LLevelSFg.pv',
            'D2_0240_B6_Mname.desc',  # 3B
            '4B_U1_0572_S8_DoorOFg.pv', '4B_U1_0573_S8_HLevelSFg.pv', '4B_U1_0574_S8_LLevelSFg.pv',
            'D2_0320_B8_Mname.desc',  # 4B
            '5B_U1_0692_S10_DoorOFg.pv', '5B_U1_0693_S10_HLevelSFg.pv', '5B_U1_0694_S10_LLevelSFg.pv',
            'D2_0400_B10_Mname.desc',  # 5B
            '6B_U1_0812_S12_DoorOFg.pv', '6B_U1_0813_S12_HLevelSFg.pv', '6B_U1_0814_S12_LLevelSFg.pv',
            'D2_0480_B12_Mname.desc',  # 6B
            '7B_U1_0932_S14_DoorOFg.pv', '7B_U1_0933_S14_HLevelSFg.pv', '7B_U1_0934_S14_LLevelSFg.pv',
            'D2_0560_B14_Mname.desc',  # 7B
            '8B_U1_1052_S16_DoorOFg.pv', '8B_U1_1053_S16_HLevelSFg.pv', '8B_U1_1054_S16_LLevelSFg.pv',
            'D2_0640_B16_Mname.desc',  # 8B
            '9B_U1_1172_S18_DoorOFg.pv', '9B_U1_1173_S18_HLevelSFg.pv', '9B_U1_1174_S18_LLevelSFg.pv',
            'D2_0720_B18_Mname.desc',  # 9B
        ]
        param = "\n".join([f"<real:string>{i[3:]}</real:string>" for i in point_name])
        """获取嘉正线体数据"""
        send_data = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:real="http://www.realinfo.com.cn/">
                           <soapenv:Header/>
                           <soapenv:Body>
                              <real:GetRealData>
                                 <!--Optional:-->
                                 <real:names>
                                    <!--Zero or more repetitions:-->
                                    {param}
                                 </real:names>
                              </real:GetRealData>
                           </soapenv:Body>
                        </soapenv:Envelope>"""
        door_info = requests.post(self.url, data=send_data.encode('utf-8'), timeout=5)
        res = door_info.content.decode('utf-8')
        result_flag = re.findall(r'<ns1:GetRealDataResult>(.*)</ns1:GetRealDataResult>', res)[0]
        if result_flag != 'true':
            raise ValueError('获取线体料位信息失败')
        rep_list = re.findall(r'<ns1:string>(.*?)</ns1:string>', res)
        if set(rep_list) & {'-9999', '9999'}:
            raise ValueError('获取料罐信息失败, 数据点返回数据异常')
        using_tank_no = list(self.queryset.values_list('tank_no', flat=True))
        for i in range(len(point_name) // 4):
            tank_no = point_name[i * 4][:2]
            now_tank_data = rep_list[i * 4: (i + 1) * 4]
            if tank_no not in using_tank_no:
                continue
            open_flag = 0 if now_tank_data[0] == '1' else 1
            status = 2 if now_tank_data[1] == '1' else (1 if now_tank_data[2] == '1' else 3)
            self.queryset.filter(equip_no=self.equip_no, tank_no=tank_no).update(
                **{'open_flag': open_flag, 'status': status})
