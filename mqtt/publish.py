import logging

from ambulance.serializers import AmbulanceSerializer
from ambulance.serializers import CallSerializer
from equipment.models import Equipment
from equipment.serializers import EquipmentItemSerializer, EquipmentSerializer
from hospital.serializers import HospitalSerializer
from login.serializers import UserProfileSerializer
from login.views import SettingsView

from environs import Env

import paho.mqtt.publish as publish

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

env = Env()
logger = logging.getLogger(__name__)


# MessagePublishClient class

class MessagePublishClient:

    def publish_message(self, **kwargs):
        pass

    def publish_settings(self, **kwargs):
        pass

    def publish_profile(self, user, **kwargs):
        pass

    def remove_profile(self, user, **kwargs):
        pass

    def publish_ambulance(self, ambulance, **kwargs):
        pass

    def remove_ambulance(self, ambulance, **kwargs):
        pass

    def publish_hospital(self, hospital, **kwargs):
        pass

    def remove_hospital(self, hospital, **kwargs):
        pass

    def publish_equipment_metadata(self, hospital, **kwargs):
        pass

    def publish_equipment_item(self, hospital, **kwargs):
        pass

    def remove_equipment_item(self, hospital, **kwargs):
        pass

    # For calls

    def publish_call(self, call, **kwargs):
        pass

    def remove_call(self, call, **kwargs):
        pass

    def publish_call_status(self, **kwargs):
        pass

    def remove_call_status(self, **kwargs):
        pass


class PublishSingle:

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def publish_topic(self, topic, payload, qos=0, retain=False):

        # serializer?
        if isinstance(payload, serializers.BaseSerializer):
            payload = JSONRenderer().render(payload.data)
        else:
            payload = JSONRenderer().render(payload)

        # Publish to topic
        publish.single(topic, payload, qos, retain, **self.kwargs)

    def remove_topic(self, topic, qos=0):

        # Publish null to retained topic
        publish.single(topic, None, qos=qos, retain=True, **self.kwargs)


class SingletonPublishClient(PublishSingle):

    def __init__(self, **kwargs):
        self.active = kwargs.pop('active', True)

        mqtt_publish = env.bool("DJANGO_ENABLE_MQTT_PUBLISH", default=True)
        if not mqtt_publish:

            self.active = False
            logger.info(">> No connection to MQTT, will not publish messages")
            return

        # initialization
        from django.conf import settings

        broker = {
            'hostname': settings.MQTT['BROKER_HOST'] if not settings.TESTING else settings.MQTT['BROKER_TEST_HOST'],
            'port': 1883,
            'auth': {
                'username': settings.MQTT['USERNAME'],
                'password': settings.MQTT['PASSWORD']
            }
        }
        broker.update(kwargs)

        super().__init__(**broker)

    def publish_topic(self, topic, payload, qos=0, retain=False):
        if self.active:
            super().publish_topic(topic, payload, qos, retain)

    def remove_topic(self, topic, qos=0):
        if self.active:
            super().remove_topic(topic, qos)

    def publish_message(self, message, qos=2):
        self.publish_topic('message',
                           message,
                           qos=qos,
                           retain=False)

    def publish_settings(self, qos=2, retain=False):
        self.publish_topic('settings',
                           SettingsView.get_settings(),
                           qos=qos,
                           retain=retain)

    def publish_profile(self, user, qos=2, retain=False):
        self.publish_topic('user/{}/profile'.format(user.username),
                           UserProfileSerializer(user),
                           qos=qos,
                           retain=retain)

    def remove_profile(self, user):
        self.remove_topic('user/{}/profile'.format(user.username))

    def publish_ambulance(self, ambulance, qos=2, retain=False):
        self.publish_topic('ambulance/{}/data'.format(ambulance.id),
                           AmbulanceSerializer(ambulance),
                           qos=qos,
                           retain=retain)

    def remove_ambulance(self, ambulance):
        self.remove_topic('ambulance/{}/data'.format(ambulance.id))

    def publish_hospital(self, hospital, qos=2, retain=False):
        self.publish_topic('hospital/{}/data'.format(hospital.id),
                           HospitalSerializer(hospital),
                           qos=qos,
                           retain=retain)

    def remove_hospital(self, hospital):
        self.remove_topic('hospital/{}/data'.format(hospital.id))
        self.remove_topic('equipment/{}/metadata'.format(hospital.equipmentholder.id))

    def publish_equipment_metadata(self, equipmentholder, qos=2, retain=False):
        equipment_items = equipmentholder.equipmentitem_set.values('equipment')
        equipments = Equipment.objects.filter(id__in=equipment_items)
        self.publish_topic('equipment/{}/metadata'.format(equipmentholder.id),
                           EquipmentSerializer(equipments, many=True),
                           qos=qos,
                           retain=retain)

    def publish_equipment_item(self, equipment_item, qos=2, retain=False):
        self.publish_topic('equipment/{}/item/{}/data'.format(equipment_item.equipmentholder.id,
                                                              equipment_item.equipment.id),
                           EquipmentItemSerializer(equipment_item),
                           qos=qos,
                           retain=retain)

    def remove_equipment_item(self, equipment_item):
        self.remove_topic('equipment/{}/item/{}/data'.format(equipment_item.equipmentholder.id,
                                                             equipment_item.equipment.id))

    def publish_call(self, call, qos=2, retain=False):
        # otherwise, publish call data
        self.publish_topic('call/{}/data'.format(call.id),
                           CallSerializer(call),
                           qos=qos,
                           retain=retain)

    def remove_call(self, call):
        # remove ambulancecall status
        for ambulancecall in call.ambulancecall_set.all():
            self.remove_call_status(ambulancecall)

        self.remove_topic('call/{}/data'.format(call.id))

    def publish_call_status(self, ambulancecall, qos=2, retain=False):
        self.publish_topic('ambulance/{}/call/{}/status'.format(ambulancecall.ambulance_id,
                                                                ambulancecall.call_id),
                           ambulancecall.status,
                           qos=qos,
                           retain=retain)

    def remove_call_status(self, ambulancecall):
        self.remove_topic('ambulance/{}/call/{}/status'.format(ambulancecall.ambulance_id,
                                                               ambulancecall.call_id))






    def publish_ambulance_message(self, ambulancecall, qos=2, retain=False):
        self.publish_topic('ambulance/{}/message'.format(ambulancecall.ambulance_id),
                           ambulancecall.text,
                           qos=qos,
                           retain=retain)

