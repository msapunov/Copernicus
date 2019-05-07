
import unittest
#from os import path
from run import app#, db, mail

TEST_DB = "test.db"


class BasicTests(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["DEBUG"] = False
        self.app = app.test_client()


        # Disable sending emails during unit testing
        #mail.init_app(app)
        self.assertEqual(app.debug, False)


    # executed after each test
    def tearDown(self):
        pass


    def test_login(self):
        response = self.app.get('/login.html', follow_redirects=True)
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()