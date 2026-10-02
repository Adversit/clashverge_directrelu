import unittest
from unittest.mock import patch
from launcher import ROOT,is_our_process,stop_server


class LauncherTests(unittest.TestCase):
    def record(self,path=None):
        return dict(ProcessId=123,ExecutablePath='C:/Python/python.exe',CommandLine='"C:/Python/python.exe" "'+str(path or ROOT/'app.py')+'"')
    def test_exact_app_path(self):
        self.assertTrue(is_our_process(self.record()))
        self.assertFalse(is_our_process(self.record(ROOT.parent/'another-project'/'app.py')))
        self.assertFalse(is_our_process(dict(self.record(),CommandLine='python.exe app.py')))
        self.assertFalse(is_our_process(dict(self.record(),ExecutablePath='C:/Apps/clash.exe')))
        self.assertFalse(is_our_process(dict(self.record(),CommandLine='python.exe -c "pass" "'+str(ROOT/'app.py')+'"')))
    def test_stop_idle(self):
        with patch('launcher.listeners',return_value=[]),patch('launcher.terminate_verified') as terminate:
            stop_server();terminate.assert_not_called()
    def test_foreign_listener_refused(self):
        with patch('launcher.listeners',return_value=[self.record(ROOT.parent/'other'/'app.py')]),patch('launcher.healthy',return_value=True),patch('launcher.terminate_verified') as terminate:
            with self.assertRaises(RuntimeError):stop_server()
            terminate.assert_not_called()
    def test_invalid_health_refused(self):
        with patch('launcher.listeners',return_value=[self.record()]),patch('launcher.healthy',return_value=False),patch('launcher.terminate_verified') as terminate:
            with self.assertRaises(RuntimeError):stop_server()
            terminate.assert_not_called()
    def test_stop_verified_listener(self):
        record=self.record()
        with patch('launcher.listeners',side_effect=[[record],[]]),patch('launcher.healthy',return_value=True),patch('launcher.terminate_verified') as terminate:
            stop_server();terminate.assert_called_once_with(record)


if __name__=='__main__':unittest.main()
