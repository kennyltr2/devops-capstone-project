"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}

######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        talisman.force_https = False
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_read_an_account(self):
        """It should read an Account"""
        accounts = self._create_accounts(5)
        account = accounts[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['id'], account.id)
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)
        self.assertEqual(data["date_joined"], str(account.date_joined))

    def test_read_no_account(self):
        """It should return no account found"""
        accounts = self._create_accounts(5)
        account = accounts[0]
        account.id = 0
        response = self.client.get(f"{BASE_URL}/{account.id}")
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_all_account(self):
        """It should list all Accounts"""
        accounts = self._create_accounts(5)
        response = self.client.get(BASE_URL)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 5)

    def test_list_no_account(self):
        """It should list return empty list and 200 if no accounts"""
        response = self.client.get(BASE_URL)
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 0)

    def test_update_account(self):
        """It should update account"""
        account = self._create_accounts(1)[0]
        account2 = AccountFactory()
        account.address = account2.address
        account.email = account2.email
        response = self.client.put(f"{BASE_URL}/{account.id}", json=account.serialize())
        data = response.get_json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["phone_number"], account.phone_number)

    def test_update_no_account(self):
        """It should return 404 if no account found"""
        accounts = self._create_accounts(5)
        account = accounts[0]
        response = self.client.put(f"{BASE_URL}/{0}", json=account.serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account(self):
        """It should delete an account"""
        account = self._create_accounts(5)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        #Check if only 1 of 5 deleted
        response = self.client.get(BASE_URL)
        data = response.get_json()
        print(data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 4)

    def test_error_handler(self):
        """Error handler should return method not allowed when an invalid request is made on an endpoint"""
        account = self._create_accounts(1)[0]
        #PUT on BASE_URL
        response = self.client.put(f"{BASE_URL}", json=account.serialize())
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        #DELETE on BASE_URL
        response = self.client.delete(f"{BASE_URL}")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        #POST on BASE_URL/<account_id>
        account = AccountFactory()
        response = self.client.post(
            f"{BASE_URL}/{account.id}",
            json=account.serialize(),
            content_type="application/json"
        )        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get('/', environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('Content-Security-Policy'), 'default-src \'self\'; object-src \'none\'')
        self.assertEqual(response.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
