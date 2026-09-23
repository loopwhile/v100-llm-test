from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import validate_repo

class RepoContractTests(unittest.TestCase):
 def test_repository_contract(self):
  self.assertEqual(validate_repo.validate(),[])
if __name__=="__main__":
 unittest.main()
