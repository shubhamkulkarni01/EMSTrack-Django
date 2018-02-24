import math
from django.test import TestCase, Client

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

from django.contrib.gis.geos import Point
from django.utils import timezone
from django.conf import settings

from rest_framework import serializers
from rest_framework.parsers import JSONParser
from io import BytesIO
import json

from login.models import AmbulancePermission, HospitalPermission

from ambulance.models import Ambulance, \
    AmbulanceStatus, AmbulanceCapability, AmbulanceUpdate
from ambulance.serializers import AmbulanceSerializer, AmbulanceUpdateSerializer

from hospital.models import Hospital, \
    Equipment, HospitalEquipment, EquipmentType
from hospital.serializers import HospitalSerializer, \
    HospitalEquipmentSerializer, EquipmentSerializer

from emstrack.tests.util import date2iso, point2str

from login.tests.setup_data import TestSetup


class TestAmbulanceGetList(TestSetup):

    def test_ambulance_serializer(self):

        # test AmbulanceSerializer
        for a in (self.a1, self.a2, self.a3):
            serializer = AmbulanceSerializer(a)
            result = {
                'id': a.id,
                'identifier': a.identifier,
                'comment': a.comment,
                'capability': a.capability,
                'status': AmbulanceStatus.UK.name,
                'orientation': a.orientation,
                'location': point2str(a.location),
                'timestamp': date2iso(a.timestamp),
                'updated_by': a.updated_by.id,
                'updated_on': date2iso(a.updated_on)
            }
            self.assertDictEqual(serializer.data, result)

    def test_ambulance_get_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve any ambulance
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any ambulance
        response = client.get('/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a2.id)).data
        self.assertDictEqual(result, answer)

        # retrieve any ambulance
        response = client.get('/api/ambulance/{}/'.format(str(self.a3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve own
        response = client.get('/api/ambulance/{}/'.format(str(self.a3.id)),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve someone else's
        response = client.get('/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # can't read
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
        
        # retrieve someone else's
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # retrieve someone else's
        response = client.get('/api/ambulance/{}/'.format(str(self.a2.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)),
                              follow=True)
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()
        
    def test_ambulance_get_list_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve ambulances
        response = client.get('/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [AmbulanceSerializer(self.a1).data,
                  AmbulanceSerializer(self.a2).data,
                  AmbulanceSerializer(self.a3).data]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve ambulances
        response = client.get('/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = []
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()
        
        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve ambulances
        response = client.get('/api/ambulance/',
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = [ # AmbulanceSerializer(self.a1).data, # can't read
                  AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data]
        self.assertCountEqual(result, answer)
        
        # logout
        client.logout()


class TestAmbulanceUpdate(TestSetup):
    
    def test_ambulance_update_serializer(self):
        
        # superuser first
        
        # Update ambulance status
        a = self.a1
        user = self.u1
        status = AmbulanceStatus.AH.name
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': status,
            'orientation': a.orientation,
            'location': point2str(a.location),
            'timestamp': date2iso(a.timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)
        
        # Update ambulance location
        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'timestamp': timestamp,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': a.status,
            'orientation': a.orientation,
            'location': point2str(location),
            'timestamp': date2iso(timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

        # error update timestamp without location or status
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'timestamp': timestamp,
                                         }, partial=True)
        self.assertEqual(serializer.is_valid(), False)
        
        # regular authorized user
        
        # Update ambulance status
        a = self.a3
        user = self.u3
        status = AmbulanceStatus.AH.name
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': status,
            'orientation': a.orientation,
            'location': point2str(a.location),
            'timestamp': date2iso(a.timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)
        
        # Update ambulance location
        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}
        
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'timestamp': timestamp
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': a.identifier,
            'comment': a.comment,
            'capability': a.capability,
            'status': a.status,
            'orientation': a.orientation,
            'location': point2str(location),
            'timestamp': date2iso(timestamp),
            'updated_by': user.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

        # error update timestamp without location or status
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'timestamp': timestamp,
                                         }, partial=True)
        self.assertEqual(serializer.is_valid(), False)
        
    def test_ambulance_patch_viewset(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve ambulance
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(self.a1).data
        self.assertDictEqual(result, answer)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        self.assertDictEqual(result, answer)

        # retrieve new ambulance status
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)

        # set status location
        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}
        
        response = client.patch('/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'location': point2str(location),
                                    'timestamp': date2iso(timestamp),
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a1.id)).data
        if math.fabs(answer['orientation'] - result['orientation']) < 1e-4:
            answer['orientation'] = result['orientation']
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance location
        response = client.get('/api/ambulance/{}/'.format(str(self.a1.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        self.assertEqual(result['location'], point2str(location))
        self.assertEqual(result['timestamp'], date2iso(timestamp))
        
        # set wrong attribute
        response = client.patch('/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': 'will fail'
                                })
        )
        self.assertEqual(response.status_code, 400)
        
        # set wrong ambulance id
        response = client.patch('/api/ambulance/100/',
                                data = json.dumps({
                                    'status': status
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        # retrieve ambulance
        response = client.get('/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(self.a3).data
        self.assertDictEqual(result, answer)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance status
        response = client.get('/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        
        # set location
        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}
        
        response = client.patch('/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'location': point2str(location),
                                    'timestamp': date2iso(timestamp),
                                })
        )
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(Ambulance.objects.get(id=self.a3.id)).data
        if math.fabs(answer['orientation'] - result['orientation']) < 1e-4:
            answer['orientation'] = result['orientation']
        self.assertDictEqual(result, answer)
        
        # retrieve new ambulance location
        response = client.get('/api/ambulance/{}/'.format(str(self.a3.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['status'], status)
        self.assertEqual(result['location'], point2str(location))
        self.assertEqual(result['timestamp'], date2iso(timestamp))
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a2.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
                
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a1.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a2.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)

        # set status ambulance
        status = AmbulanceStatus.OS.name
        response = client.patch('/api/ambulance/{}/'.format(str(self.a3.id)),
                                content_type='application/json',
                                data = json.dumps({
                                    'status': status,
                                })
        )
        self.assertEqual(response.status_code, 404)
        
        # logout
        client.logout()


class TestAmbulanceCreate(TestSetup):

    def test_ambulance_create_serializer(self):

        serializer = AmbulanceSerializer(data={
            'identifier': 'NEW-1897',
            'capability': AmbulanceCapability.R.name,
            'comment': 'no comments'
        })
        serializer.is_valid()
        serializer.save(updated_by = self.u1)
        
        # test AmbulanceSerializer
        a = Ambulance.objects.get(identifier='NEW-1897')
        serializer = AmbulanceSerializer(a)
        result = {
            'id': a.id,
            'identifier': 'NEW-1897',
            'comment': 'no comments',
            'capability': AmbulanceCapability.R.name,
            'status': AmbulanceStatus.UK.name,
            'orientation': a.orientation,
            'location': point2str(a.location),
            'timestamp': date2iso(a.timestamp),
            'updated_by': self.u1.id,
            'updated_on': date2iso(a.updated_on)
        }
        self.assertDictEqual(serializer.data, result)

    def test_ambulance_post_view(self):

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # create ambulance
        response = client.post('/api/ambulance/',
                               {
                                   'identifier': 'NEW-1897',
                                   'capability': AmbulanceCapability.R.name,
                                   'comment': 'no comments'
                               }
        )
        self.assertEqual(response.status_code, 201)
        a = Ambulance.objects.get(identifier='NEW-1897')
        
        # retrieve ambulance
        response = client.get('/api/ambulance/{}/'.format(str(a.id)))
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        answer = AmbulanceSerializer(a).data
        self.assertDictEqual(result, answer)

        # create ambulance (repeated identifier)
        response = client.post('/api/ambulance/',
                               {
                                   'identifier': 'NEW-1897',
                                   'capability': AmbulanceCapability.R.name,
                                   'comment': 'no comments'
                               }
        )
        self.assertEqual(response.status_code, 400)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertEqual(result['identifier'],
                         ['ambulance with this identifier already exists.'])
        
        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')
        
        response = client.post('/api/ambulance/',
                               {
                                   'identifier': 'NEW-NEW-1897',
                                   'capability': AmbulanceCapability.B.name,
                                   'comment': 'more comments'
                               }
        )
        self.assertEqual(response.status_code, 403)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')
                
        response = client.post('/api/ambulance/',
                               {
                                   'identifier': 'NEW-NEW-1897',
                                   'capability': AmbulanceCapability.B.name,
                                   'comment': 'more comments'
                               }
        )
        self.assertEqual(response.status_code, 403)
        
        # logout
        client.logout()


class TestAmbulanceUpdates(TestSetup):

    def test(self):
        
        # Update ambulance a1
        a = self.a1
        user = self.u1

        status = AmbulanceStatus.AH.name
        serializer = AmbulanceSerializer(Ambulance.objects.get(id=a.id),
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}

        serializer = AmbulanceSerializer(Ambulance.objects.get(id=a.id),
                                         data={
                                             'location': location,
                                             'timestamp': timestamp
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)
        
        status = AmbulanceStatus.OS.name
        serializer = AmbulanceSerializer(Ambulance.objects.get(id=a.id),
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # This update does not go to AmbulanceUpdate!
        serializer = AmbulanceSerializer(Ambulance.objects.get(id=a.id),
                                         data={
                                             'identifier': 'someid',
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test AmbulanceUpdateSerializer
        queryset = AmbulanceUpdate.objects.filter(ambulance=a)
        answer1 = []
        for u in queryset:
            serializer = AmbulanceUpdateSerializer(u)
            result = {
                'id': u.id,
                'ambulance_id': u.ambulance.id,
                'ambulance_identifier': u.ambulance.identifier,
                'comment': u.comment,
                'status': u.status,
                'orientation': u.orientation,
                'location': point2str(u.location),
                'timestamp': date2iso(u.timestamp),
                'updated_by_username': u.updated_by.username,
                'updated_on': date2iso(u.updated_on)
            }
            answer1.append(serializer.data)
            self.assertDictEqual(serializer.data, result)

        # Update ambulance a2
        a = self.a3
        user = self.u3

        status = AmbulanceStatus.AH.name
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}

        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'timestamp': timestamp
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        status = AmbulanceStatus.OS.name
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test AmbulanceUpdateSerializer
        queryset = AmbulanceUpdate.objects.filter(ambulance=a)
        answer3 = []
        for u in queryset:
            serializer = AmbulanceUpdateSerializer(u)
            result = {
                'id': u.id,
                'ambulance_id': u.ambulance.id,
                'ambulance_identifier': a.identifier,
                'comment': u.comment,
                'status': u.status,
                'orientation': u.orientation,
                'location': point2str(u.location),
                'timestamp': date2iso(u.timestamp),
                'updated_by_username': u.updated_by.username,
                'updated_on': date2iso(u.updated_on)
            }
            answer3.append(serializer.data)
            self.assertDictEqual(serializer.data, result)

        # Test api

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer1)
        self.assertEqual(len(result['results']), 4)

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer3)
        self.assertEqual(len(result['results']), 4)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer3)
        self.assertEqual(len(result['results']), 4)

        # logout
        client.logout()


class TestAmbulanceBulkUpdates(TestSetup):

    def test(self):

        # Bulk update ambulance a1
        a = self.a1
        user = self.u1

        data = [
            { 'status': AmbulanceStatus.AH.name },
            {
                'location': {'latitude': -2., 'longitude': 7.},
                'timestamp': timezone.now()
            },
            { 'status': AmbulanceStatus.OS.name }
        ]

        serializer = AmbulanceUpdateSerializer(data=data, many=True, partial=True)
        valid = serializer.is_valid()
        if not valid:
            print('errors = {}'.format(serializer.errors))
        self.assertEqual(True, valid)
        serializer.save(ambulance=Ambulance.objects.get(id=a.id),
                        updated_by=user)

        # test AmbulanceUpdateSerializer
        queryset = AmbulanceUpdate.objects.filter(ambulance=a)
        answer1 = []
        for u in queryset:
            serializer = AmbulanceUpdateSerializer(u)
            result = {
                'id': u.id,
                'ambulance_id': u.ambulance.id,
                'ambulance_identifier': u.ambulance.identifier,
                'comment': u.comment,
                'status': u.status,
                'orientation': u.orientation,
                'location': point2str(u.location),
                'timestamp': date2iso(u.timestamp),
                'updated_by_username': u.updated_by.username,
                'updated_on': date2iso(u.updated_on)
            }
            answer1.append(serializer.data)
            self.assertDictEqual(serializer.data, result)

    def _test(self):

        # Bulk update ambulance a2
        a = self.a3
        user = self.u3

        status = AmbulanceStatus.AH.name
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        timestamp = timezone.now()
        location = {'latitude': -2., 'longitude': 7.}

        serializer = AmbulanceSerializer(a,
                                         data={
                                             'location': location,
                                             'timestamp': timestamp
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        status = AmbulanceStatus.OS.name
        serializer = AmbulanceSerializer(a,
                                         data={
                                             'status': status,
                                         }, partial=True)
        serializer.is_valid()
        serializer.save(updated_by=user)

        # test AmbulanceUpdateSerializer
        queryset = AmbulanceUpdate.objects.filter(ambulance=a)
        answer3 = []
        for u in queryset:
            serializer = AmbulanceUpdateSerializer(u)
            result = {
                'id': u.id,
                'ambulance_identifier': a.identifier,
                'comment': u.comment,
                'status': u.status,
                'orientation': u.orientation,
                'location': point2str(u.location),
                'timestamp': date2iso(u.timestamp),
                'updated_by': u.updated_by.id,
                'updated_by_username': u.updated_by.username,
                'updated_on': date2iso(u.updated_on)
            }
            answer3.append(serializer.data)
            self.assertDictEqual(serializer.data, result)

        # Test api

        # instantiate client
        client = Client()

        # login as admin
        client.login(username=settings.MQTT['USERNAME'], password=settings.MQTT['PASSWORD'])

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer1)
        self.assertEqual(len(result['results']), 4)

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer3)
        self.assertEqual(len(result['results']), 4)

        # logout
        client.logout()

        # login as testuser1
        client.login(username='testuser1', password='top_secret')

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # logout
        client.logout()

        # login as testuser2
        client.login(username='testuser2', password='very_secret')

        # retrieve ambulances
        response = client.get('/api/ambulance/{}/updates/'.format(self.a1.id),
                              follow=True)
        self.assertEqual(response.status_code, 404)

        # retrieve ambulances updates
        response = client.get('/api/ambulance/{}/updates/'.format(self.a3.id),
                              follow=True)
        self.assertEqual(response.status_code, 200)
        result = JSONParser().parse(BytesIO(response.content))
        self.assertCountEqual(result['results'], answer3)
        self.assertEqual(len(result['results']), 4)

        # logout
        client.logout()
