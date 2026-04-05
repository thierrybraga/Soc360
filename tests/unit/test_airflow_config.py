import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock Airflow modules BEFORE importing DAGs
sys.modules['airflow'] = MagicMock()
sys.modules['airflow.models'] = MagicMock()
sys.modules['airflow.providers.http.operators.http'] = MagicMock()
sys.modules['airflow.providers.http.sensors.http'] = MagicMock()
sys.modules['airflow.operators.trigger_dagrun'] = MagicMock()
sys.modules['airflow.utils.dates'] = MagicMock()

# Setup Variable.get mock
mock_variable = MagicMock()
sys.modules['airflow.models'].Variable = mock_variable

# Setup DAG mock
mock_dag = MagicMock()
sys.modules['airflow'].DAG = mock_dag

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestAirflowConfig(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_variable.reset_mock()
        mock_dag.reset_mock()
        
        # Configure Variable.get to return values based on key
        def variable_get_side_effect(key, default_var=None):
            if key == "open_monitor_api_conn_id":
                return os.environ.get('AIRFLOW_VAR_OPEN_MONITOR_API_CONN_ID', default_var)
            if key == "admin_email":
                return os.environ.get('AIRFLOW_VAR_ADMIN_EMAIL', default_var)
            return default_var
            
        mock_variable.get.side_effect = variable_get_side_effect

        # Set environment variables
        os.environ['AIRFLOW_VAR_OPEN_MONITOR_API_CONN_ID'] = 'env_conn_id'
        os.environ['AIRFLOW_VAR_ADMIN_EMAIL'] = 'env_email@example.com'

    def test_nvd_sync_dag_config(self):
        # Import DAG module
        if 'dags.nvd_sync' in sys.modules:
            del sys.modules['dags.nvd_sync']
        import dags.nvd_sync
        
        # Verify Variable.get was called
        mock_variable.get.assert_any_call("open_monitor_api_conn_id", default_var="open_monitor_api")
        mock_variable.get.assert_any_call("admin_email", default_var="admin@openmonitor.local")
        
        # Check if values were assigned correctly in module
        self.assertEqual(dags.nvd_sync.API_CONN_ID, 'env_conn_id')
        self.assertEqual(dags.nvd_sync.ADMIN_EMAIL, 'env_email@example.com')

    def test_euvd_sync_dag_config(self):
        if 'dags.euvd_sync' in sys.modules:
            del sys.modules['dags.euvd_sync']
        import dags.euvd_sync
        
        self.assertEqual(dags.euvd_sync.API_CONN_ID, 'env_conn_id')
        self.assertEqual(dags.euvd_sync.ADMIN_EMAIL, 'env_email@example.com')

    def test_mitre_sync_dag_config(self):
        if 'dags.mitre_sync' in sys.modules:
            del sys.modules['dags.mitre_sync']
        import dags.mitre_sync
        
        self.assertEqual(dags.mitre_sync.API_CONN_ID, 'env_conn_id')
        self.assertEqual(dags.mitre_sync.ADMIN_EMAIL, 'env_email@example.com')

if __name__ == '__main__':
    unittest.main()
