import pytest
import base64
from unittest.mock import patch
from topdesk_mcp._topdesk_sdk import connect

@pytest.fixture
def topdesk_credentials():
    url = "https://test.topdesk.net"
    username = "test_user"
    password = "test_password"
    credpair = (base64.b64encode((username + ':' + password).encode("utf-8"))).decode("utf-8")
    return url, username, password, credpair

@pytest.fixture
def topdesk_connect(topdesk_credentials):
    with patch('topdesk_mcp._incident.incident'), \
         patch('topdesk_mcp._person.person'), \
         patch('topdesk_mcp._operator.operator'):
        url, username, password, _ = topdesk_credentials
        return connect(url, username, password)

class TestTopdeskConnect:
    def test_initialization(self, topdesk_connect, topdesk_credentials):
        url, username, password, credpair = topdesk_credentials
        assert topdesk_connect._topdesk_url == url
        assert topdesk_connect._credpair == credpair
        
        # Check that all modules are initialized
        assert hasattr(topdesk_connect, 'incident')
        assert hasattr(topdesk_connect, 'person')
        assert hasattr(topdesk_connect, 'utils')
        assert hasattr(topdesk_connect, 'department')
        assert hasattr(topdesk_connect, 'branch')
        assert hasattr(topdesk_connect, 'location')
        assert hasattr(topdesk_connect, 'supplier')
        assert hasattr(topdesk_connect, 'operatorgroup')
        assert hasattr(topdesk_connect, 'operator')
        assert hasattr(topdesk_connect, 'budgetholder')
        assert hasattr(topdesk_connect, 'operational_activities')

    def test_get_countries(self, topdesk_connect):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Country1", "Country2"]) as mock_handle:
            result = topdesk_connect.get_countries()
            mock_request.assert_called_once_with("/tas/api/countries")
            mock_handle.assert_called_once_with("raw_response")
            assert result == ["Country1", "Country2"]

    def test_get_archiving_reasons(self, topdesk_connect):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Reason1", "Reason2"]) as mock_handle:
            result = topdesk_connect.get_archiving_reasons()
            mock_request.assert_called_once_with("/tas/api/archiving-reasons")
            mock_handle.assert_called_once_with("raw_response")
            assert result == ["Reason1", "Reason2"]

    def test_get_timespent_reasons(self, topdesk_connect):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Reason1", "Reason2"]) as mock_handle:
            result = topdesk_connect.get_timespent_reasons()
            mock_request.assert_called_once_with("/tas/api/timespent-reasons")
            mock_handle.assert_called_once_with("raw_response")
            assert result == ["Reason1", "Reason2"]

    def test_get_permissiongroups(self, topdesk_connect):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Group1", "Group2"]) as mock_handle:
            result = topdesk_connect.get_permissiongroups()
            mock_request.assert_called_once_with("/tas/api/permissiongroups")
            mock_handle.assert_called_once_with("raw_response")
            assert result == ["Group1", "Group2"]

    def test_notification(self, topdesk_connect):
        with patch('topdesk_mcp._utils.utils.add_id_jsonbody', return_value={"title": "Test Title", "extra": "data"}) as mock_add_id, \
             patch('topdesk_mcp._utils.utils.post_to_topdesk', return_value="raw_response") as mock_post, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"status": "success"}) as mock_handle:
            result = topdesk_connect.notification("Test Title", extra="data")
            mock_add_id.assert_called_once_with(title="Test Title", extra="data")
            mock_post.assert_called_once_with(
                "/tas/api/tasknotifications/custom",
                {"title": "Test Title", "extra": "data"}
            )
            assert result == {"status": "success"}

class TestOperatorGroup:
    @pytest.fixture
    def operatorgroup(self, topdesk_connect):
        return topdesk_connect.operatorgroup
    
    def test_get_operators(self, operatorgroup):
        operatorgroup_id = "123"
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Operator1", "Operator2"]) as mock_handle:
            result = operatorgroup.get_operators(operatorgroup_id)
            mock_request.assert_called_once_with(f"/tas/api/operatorgroups/id/{operatorgroup_id}/operators")
            mock_handle.assert_called_once_with("raw_response")
            assert result == ["Operator1", "Operator2"]
    
    def test_get_list(self, operatorgroup):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Group1", "Group2"]) as mock_handle:
            result = operatorgroup.get_list(archived=True, page_size=50, query="test")
            mock_request.assert_called_once_with("/tas/api/operatorgroups", True, 50, "test")
            assert result == ["Group1", "Group2"]

    def test_get_id_operatorgroup(self, operatorgroup):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=[
                 {"id": "123", "groupName": "Test Group"},
                 {"id": "456", "groupName": "Another Group"}
             ]) as mock_handle, \
             patch('topdesk_mcp._utils.utils.resolve_lookup_candidates', return_value="123") as mock_resolve:
            result = operatorgroup.get_id_operatorgroup("Test")
            mock_resolve.assert_called_once()
            assert result == "123"
    
    def test_create(self, operatorgroup):
        with patch('topdesk_mcp._utils.utils.add_id_jsonbody', return_value={"groupName": "New Group", "extra": "data"}) as mock_add_id, \
             patch('topdesk_mcp._utils.utils.post_to_topdesk', return_value="raw_response") as mock_post, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "789", "groupName": "New Group"}) as mock_handle:
            result = operatorgroup.create("New Group", extra="data")
            mock_add_id.assert_called_once_with(groupName="New Group", extra="data")
            mock_post.assert_called_once_with(
                "/tas/api/operatorgroups", 
                {"groupName": "New Group", "extra": "data"}
            )
            assert result == {"id": "789", "groupName": "New Group"}
        
    def test_update(self, operatorgroup):
        operatorgroup_id = "123"
        with patch('topdesk_mcp._utils.utils.add_id_jsonbody', return_value={"groupName": "Updated Group"}) as mock_add_id, \
             patch('topdesk_mcp._utils.utils.put_to_topdesk', return_value="raw_response") as mock_put, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "123", "groupName": "Updated Group"}) as mock_handle:
            result = operatorgroup.update(operatorgroup_id, groupName="Updated Group")
            mock_add_id.assert_called_once_with(groupName="Updated Group")
            mock_put.assert_called_once_with(
                f"/tas/api/operatorgroups/id/{operatorgroup_id}", 
                {"groupName": "Updated Group"}
            )
            assert result == {"id": "123", "groupName": "Updated Group"}

    def test_archive(self, operatorgroup):
        operatorgroup_id = "123"
        reason_id = "456"
        with patch('topdesk_mcp._utils.utils.put_to_topdesk', return_value="raw_response") as mock_put, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"status": "archived"}) as mock_handle:
            result = operatorgroup.archive(operatorgroup_id, reason_id)
            mock_put.assert_called_once()
            assert result == {"status": "archived"}
    
    def test_unarchive(self, operatorgroup):
        operatorgroup_id = "123"
        with patch('topdesk_mcp._utils.utils.put_to_topdesk', return_value="raw_response") as mock_put, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"status": "unarchived"}) as mock_handle:
            result = operatorgroup.unarchive(operatorgroup_id)
            mock_put.assert_called_once_with(
                f"/tas/api/operatorgroups/id/{operatorgroup_id}/unarchive", 
                None
            )
            assert result == {"status": "unarchived"}

class TestSupplier:
    @pytest.fixture
    def supplier(self, topdesk_connect):
        return topdesk_connect.supplier
    
    def test_get(self, supplier):
        supplier_id = "123"
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "123", "name": "Test Supplier"}) as mock_handle:
            result = supplier.get(supplier_id)
            mock_request.assert_called_once_with(f"/tas/api/suppliers/{supplier_id}")
            assert result == {"id": "123", "name": "Test Supplier"}
    
    def test_get_list(self, supplier):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Supplier1", "Supplier2"]) as mock_handle:
            result = supplier.get_list(archived=True, page_size=50, query="test")
            mock_request.assert_called_once_with("/tas/api/suppliers", True, 50, "test")
            assert result == ["Supplier1", "Supplier2"]

class TestLocation:
    @pytest.fixture
    def location(self, topdesk_connect):
        return topdesk_connect.location
    
    def test_get_list(self, location):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Location1", "Location2"]) as mock_handle:
            result = location.get_list(archived=True, page_size=50, query="test")
            mock_request.assert_called_once_with("/tas/api/locations", True, 50, "test")
            assert result == ["Location1", "Location2"]
    
    def test_get(self, location):
        location_id = "123"
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "123", "name": "Test Location"}) as mock_handle:
            result = location.get(location_id)
            mock_request.assert_called_once_with(f"/tas/api/locations/id/{location_id}")
            assert result == {"id": "123", "name": "Test Location"}

class TestBranch:
    @pytest.fixture
    def branch(self, topdesk_connect):
        return topdesk_connect.branch
    
    def test_get_list(self, branch):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Branch1", "Branch2"]) as mock_handle:
            result = branch.get_list(archived=True, page_size=50, query="test")
            mock_request.assert_called_once_with("/tas/api/branches", True, 50, "test")
            assert result == ["Branch1", "Branch2"]
        
    def test_get(self, branch):
        branch_id = "123"
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "123", "name": "Test Branch"}) as mock_handle:
            result = branch.get(branch_id)
            mock_request.assert_called_once_with(f"/tas/api/branches/id/{branch_id}")
            assert result == {"id": "123", "name": "Test Branch"}

class TestOperationalActivities:
    @pytest.fixture
    def operational_activities(self, topdesk_connect):
        return topdesk_connect.operational_activities
    
    def test_get_list(self, operational_activities):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Activity1", "Activity2"]) as mock_handle:
            kwargs = {"param1": "value1", "param2": "value2"}
            result = operational_activities.get_list(**kwargs)
            mock_request.assert_called_once_with("/tas/api/operationalActivities", extended_uri=kwargs)
            assert result == ["Activity1", "Activity2"]
    
    def test_get(self, operational_activities):
        activity_id = "123"
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "123", "name": "Test Activity"}) as mock_handle:
            result = operational_activities.get(activity_id)
            mock_request.assert_called_once_with(f"/tas/api/operationalActivities/{activity_id}")
            assert result == {"id": "123", "name": "Test Activity"}

class TestDepartment:
    @pytest.fixture
    def department(self, topdesk_connect):
        return topdesk_connect.department
    
    def test_get_list(self, department):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Department1", "Department2"]) as mock_handle:
            result = department.get_list(archived=True, page_size=50)
            mock_request.assert_called_once_with("/tas/api/departments", True, 50)
            assert result == ["Department1", "Department2"]
        
    def test_create(self, department):
        with patch('topdesk_mcp._utils.utils.add_id_jsonbody', return_value={"name": "New Department", "extra": "data"}) as mock_add_id, \
             patch('topdesk_mcp._utils.utils.post_to_topdesk', return_value="raw_response") as mock_post, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "789", "name": "New Department"}) as mock_handle:
            result = department.create("New Department", extra="data")
            mock_add_id.assert_called_once_with(name="New Department", extra="data")
            mock_post.assert_called_once_with(
                "/tas/api/departments", 
                {"name": "New Department", "extra": "data"}
            )
            assert result == {"id": "789", "name": "New Department"}

class TestBudgetholder:
    @pytest.fixture
    def budgetholder(self, topdesk_connect):
        return topdesk_connect.budgetholder
    
    def test_get_list(self, budgetholder):
        with patch('topdesk_mcp._utils.utils.request_topdesk', return_value="raw_response") as mock_request, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value=["Budgetholder1", "Budgetholder2"]) as mock_handle:
            result = budgetholder.get_list()
            mock_request.assert_called_once_with("/tas/api/budgetholders")
            assert result == ["Budgetholder1", "Budgetholder2"]
        
    def test_create(self, budgetholder):
        with patch('topdesk_mcp._utils.utils.add_id_jsonbody', return_value={"name": "New Budgetholder", "extra": "data"}) as mock_add_id, \
             patch('topdesk_mcp._utils.utils.post_to_topdesk', return_value="raw_response") as mock_post, \
             patch('topdesk_mcp._utils.utils.handle_topdesk_response', return_value={"id": "789", "name": "New Budgetholder"}) as mock_handle:
            result = budgetholder.create("New Budgetholder", extra="data")
            mock_add_id.assert_called_once_with(name="New Budgetholder", extra="data")
            mock_post.assert_called_once_with(
                "/tas/api/branches",  # Note: using branches endpoint
                {"name": "New Budgetholder", "extra": "data"}
            )
            assert result == {"id": "789", "name": "New Budgetholder"}