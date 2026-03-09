import pytest
from django.urls import reverse
from rest_framework import status
from apps.drivers.models import Driver, DriverStats, DriverDocument
import apps.drivers.admin_views

@pytest.mark.django_db
class TestAdminDriverActions:
    @pytest.fixture
    def admin_client(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        return api_client

    def test_list_drivers_filtering(self, admin_client, driver_user):
        url = reverse('admin-drivers-list')
        # Test status filter
        response = admin_client.get(url, {"status": "ONLINE"})
        assert response.status_code == status.HTTP_200_OK
        
        # Test level filter
        response = admin_client.get(url, {"level": "NORMAL"})
        assert response.status_code == status.HTTP_200_OK

    def test_admin_driver_detail(self, admin_client, driver_user):
        url = reverse('admin-driver-detail', kwargs={'driver_id': driver_user.driver.id})
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['driver_id'] == driver_user.driver.id

    def test_admin_driver_action_suspend(self, admin_client, driver_user):
        url = reverse('admin-drivers-action')
        data = {"driver_id": driver_user.driver.id, "action": "suspend"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        driver_user.driver.refresh_from_db()
        assert driver_user.driver.stats.is_suspended is True

    def test_admin_driver_action_block(self, admin_client, driver_user):
        url = reverse('admin-drivers-action')
        data = {"driver_id": driver_user.driver.id, "action": "block"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        driver_user.driver.refresh_from_db()
        assert driver_user.driver.status == Driver.Status.BLOCKED

    def test_admin_set_driver_level(self, admin_client, driver_user):
        url = reverse('admin-driver-level', kwargs={'driver_id': driver_user.driver.id})
        data = {"level": "PRO", "reason": "Consistent performance"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        driver_user.driver.refresh_from_db()
        assert driver_user.driver.level == "PRO"

    def test_admin_approve_document(self, admin_client, driver_user):
        doc = DriverDocument.objects.create(
            driver=driver_user.driver,
            document_type="DL",
            file_path="test.pdf",
            status=DriverDocument.Status.PENDING
        )
        url = reverse('admin-doc-approve', kwargs={'doc_id': doc.id})
        data = {"action": "approve"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.status == DriverDocument.Status.APPROVED

    def test_admin_reject_document(self, admin_client, driver_user):
        doc = DriverDocument.objects.create(
            driver=driver_user.driver,
            document_type="DL",
            file_path="test.pdf",
            status=DriverDocument.Status.PENDING
        )
        url = reverse('admin-doc-approve', kwargs={'doc_id': doc.id})
        data = {"action": "reject", "reason": "Blurry image"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        doc.refresh_from_db()
        assert doc.status == DriverDocument.Status.REJECTED
        assert doc.rejection_reason == "Blurry image"

    def test_admin_driver_action_invalid_action(self, admin_client, driver_user):
        url = reverse('admin-drivers-action')
        data = {"driver_id": driver_user.driver.id, "action": "promote_to_ceo"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_driver_action_missing_id(self, admin_client):
        url = reverse('admin-drivers-action')
        data = {"action": "suspend"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    def test_admin_driver_action_force_offline(self, admin_client, driver_user):
        driver = driver_user.driver
        driver.status = Driver.Status.ONLINE
        driver.save()
        
        url = reverse('admin-drivers-action')
        data = {"driver_id": driver.id, "action": "force_offline"}
        response = admin_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        driver.refresh_from_db()
        assert driver.status == Driver.Status.OFFLINE
