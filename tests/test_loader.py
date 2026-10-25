import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build import redirect_vulkan
class LoaderTests(unittest.TestCase):
 def test_equal_length_dependency_redirect(self):
  source=b'\x7fELF'+bytes(64)+b'libvulkan.so\0'+b'unrelated'
  result=redirect_vulkan(source)
  self.assertEqual(len(source),len(result));self.assertIn(b'libogvulk.so\0',result)
  self.assertEqual(result.replace(b'libogvulk.so\0',b'libvulkan.so\0'),source)
 def test_rejects_unexpected_payloads(self):
  for source in [b'not an ELF',b'\x7fELF',b'\x7fELFlibvulkan.so\0libvulkan.so\0']:
   with self.assertRaises(ValueError):redirect_vulkan(source)
if __name__=='__main__':unittest.main()
