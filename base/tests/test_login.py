import unittest
from base import app


class CodeTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        self.app = app.test_client()
        self.assertEqual(app.debug, False)

    def tearDown(self):
        pass

    def login(self, login, password):
        return self.app.post(
            "/login.html",
            data=dict(login=login, passw=password),
            follow_redirects=True
        )

    def login_page(self, html):
        self.assertTrue("<input class=\"uk-width-1-1 uk-form-large\" "
                        "id=\"login\" name=\"login\" placeholder=\"username\" "
                        "required type=\"text\" value=\"\">" in html)
        self.assertTrue("<input class=\"uk-width-1-1 uk-form-large\" "
                        "id=\"passw\" name=\"passw\" placeholder=\"password\" "
                        "required type=\"password\" value=\"\">" in html)
        self.assertTrue("<button class=\"uk-width-1-1 uk-button "
                        "uk-button-primary uk-button-large\" type=\"submit\">"
                        "Submit</button>" in html)
        self.assertTrue("Use the same username and password as for the access "
                        "via SSH" in html)
        self.assertTrue("If you can not login, please <a href=\"#\" "
                        "onclick=mail()>contact support team</a>" in html)

    def test_login_form(self):
        response = self.app.get('/login.html')
        self.assertEqual(response.status_code, 200)
        received = response.get_data(as_text=True)
        self.login_page(received)

    def test_valid_login(self):
        self.app.get("/login.html", follow_redirects=True)
        response = self.login("msapunov", "gromozeka@88")
        self.assertIn(b"Login: &lt;User msapunov&gt;", response.data)

    def test_login_without_registering(self):
        self.app.get('/login.html', follow_redirects=True)
        response = self.login("patkennedy79@gmail.com", "FlaskIsAwesome")
        received = response.get_data(as_text=True)
        print(received)
        self.assertIn(b'ERROR! Incorrect login credentials.', response.data)

    def test_valid_logout(self):
        self.test_valid_login()
        response = self.app.get('/logout', follow_redirects=True)
        received = response.get_data(as_text=True)
        self.login_page(received)

    def test_invalid_logout_within_being_logged_in(self):
        response = self.app.get('/logout', follow_redirects=True)
        received = response.get_data(as_text=True)
        self.login_page(received)



if __name__ == "__main__":
    unittest.main()
