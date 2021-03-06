__author__ = 'isparks'

import unittest
import rwslib
import httpretty
import requests
import socket
import errno

class VersionTest(unittest.TestCase):
    """Test for the version method"""
    @httpretty.activate
    def test_version(self):
        """A simple test, patching the get request so that it does not hit a website"""

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=200,
            body="1.0.0")

        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        v = rave.send_request(rwslib.rws_requests.VersionRequest())

        self.assertEqual(v, '1.0.0')
        self.assertEqual(rave.last_result.status_code,200)

    @httpretty.activate
    def test_connection_failure(self):
        """Test we get a failure if we do not retry"""
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')


        class FailResponse():
            """A fake response that will raise a connection error as if socket connection failed"""
            def fill_filekind(self, fk):
                raise socket.error(errno.ECONNREFUSED, "Refused")


        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
                 responses=[
                               FailResponse(), #First try
                            ])


        #Now my test
        def do():
            v = rave.send_request(rwslib.rws_requests.VersionRequest())

        self.assertRaises(requests.ConnectionError, do)


    @httpretty.activate
    def test_version_with_retry(self):
        """A simple test that fails with a socket error on first attempts"""
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')


        class FailResponse():
            """A fake response that will raise a connection error as if socket connection failed"""
            def fill_filekind(self, fk):
                raise socket.error(errno.ECONNREFUSED, "Refused")


        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
                 responses=[
                               FailResponse(), #First try
                               FailResponse(), # Retry 1
                               FailResponse(), # Retry 2
                               httpretty.Response(body='1.0.0', status=200), #Retry 3
                            ])


        #Make request
        v = rave.send_request(rwslib.rws_requests.VersionRequest(), retries=3)

        self.assertEqual(v, '1.0.0')
        self.assertEqual(rave.last_result.status_code,200)

class TestMustBeRWSRequestSubclass(unittest.TestCase):
    """Test that request object passed must be RWSRequest subclass"""
    def test_basic(self):
        """Must be rwssubclass or ValueError"""

        def do():
            rave = rwslib.RWSConnection('test')
            v = rave.send_request(object())


        self.assertRaises(ValueError, do)


class RequestTime(unittest.TestCase):
    """Test for the last request time property"""
    @httpretty.activate
    def test_request_time(self):
        """A simple test, patching the get request so that it does not hit a website"""

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=200,
            body="1.0.0")

        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        v = rave.send_request(rwslib.rws_requests.VersionRequest())
        request_time = rave.request_time
        self.assertIs(type(request_time),float)

class TestErrorResponse(unittest.TestCase):

    @httpretty.activate
    def test_503_error(self):
        """Test that when we don't attempt to XMLParse a non-xml response"""

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=503,
            body='HTTP 503 Service Temporarily Unavailable')
        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(rwslib.RWSException) as exc:
            v = rave.send_request(rwslib.rws_requests.VersionRequest())
        self.assertEqual('HTTP 503 Service Temporarily Unavailable', exc.exception.rws_error)
        self.assertEqual('Unexpected Status Code (503)', exc.exception.message)

    @httpretty.activate
    def test_500_error(self):
        """Test that when we don't attempt to XMLParse a non-xml response"""

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=500,
            body='HTTP 500.13 Web server is too busy.')
        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(rwslib.RWSException) as exc:
            v = rave.send_request(rwslib.rws_requests.VersionRequest())
        self.assertEqual('HTTP 500.13 Web server is too busy.', exc.exception.rws_error)
        self.assertEqual('Server Error (500)', exc.exception.message)

    @httpretty.activate
    def test_400_error_error_response(self):
        """Parse the IIS Response Error structure"""

        text = """<Response
        ReferenceNumber="5b1fa9a3-0cf3-46b6-8304-37c2e3b7d04f5"
        InboundODMFileOID="1"
        IsTransactionSuccessful = "0"
        ReasonCode="RWS00024"
        ErrorOriginLocation="/ODM/ClinicalData[1]/SubjectData[1]"
        SuccessStatistics="Rave objects touched: Subjects=0; Folders=0; Forms=0; Fields=0; LogLines=0"
        ErrorClientResponseMessage="Subject already exists.">
        </Response>
        """.decode('utf-8')

        httpretty.register_uri(
            httpretty.POST, "https://innovate.mdsol.com/RaveWebServices/webservice.aspx?PostODMClinicalData",
            status=400,
            body=text)

        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(rwslib.RWSException) as exc:
            v = rave.send_request(rwslib.rws_requests.PostDataRequest("<ODM/>"))
        self.assertEqual('Subject already exists.', exc.exception.message)

    @httpretty.activate
    def test_400_error_iis_error(self):
        """Test that when we don't attempt to XMLParse a non-xml response"""

        text = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>OOPS! Error Occurred. Sorry about this.</title>
        </head>
        <body>
            <h2>OOPS! Error Occurred</h2>
        </body>
        </html>
        """.decode('utf-8')

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=400,
            body=text)

        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(rwslib.RWSException) as exc:
            v = rave.send_request(rwslib.rws_requests.VersionRequest())
        self.assertEqual('IIS Error', exc.exception.message)

    @httpretty.activate
    def test_400_error_ODM_error(self):
        """Test that when we don't attempt to XMLParse a non-xml response"""

        text = """
        <?xml version="1.0" encoding="utf-8"?>
        <ODM xmlns:mdsol="http://www.mdsol.com/ns/odm/metadata"
         FileType="Snapshot"
         CreationDateTime="2013-04-08T10:28:49.578-00:00"
         FileOID="4d13722a-ceb6-4419-a917-b6ad5d0bc30e"
         ODMVersion="1.3"
         mdsol:ErrorDescription="Incorrect login and password combination. [RWS00008]"
         xmlns="http://www.cdisc.org/ns/odm/v1.3" />

        """.decode('utf-8')

        httpretty.register_uri(
            httpretty.GET, "https://innovate.mdsol.com/RaveWebServices/version",
            status=400,
            body=text)

        #Now my test
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(rwslib.RWSException) as exc:
            v = rave.send_request(rwslib.rws_requests.VersionRequest())
        self.assertEqual('Incorrect login and password combination. [RWS00008]', exc.exception.message)


class Timeout(unittest.TestCase):

    def test_timeout(self):
        """Test against an external website to verify timeout (mocking doesn't help as far as I can work out)"""

        #Test that unauthorised request times out
        rave = rwslib.RWSConnection('https://innovate.mdsol.com')
        with self.assertRaises(requests.exceptions.Timeout):
            rave.send_request(rwslib.rws_requests.ClinicalStudiesRequest(),timeout=0.0001)

        #Raise timeout and check no timeout occurs.  An exception will be raised because the request is unauthorised
        with self.assertRaises(rwslib.RWSException):
            rave.send_request(rwslib.rws_requests.ClinicalStudiesRequest(),timeout=3600)


if __name__ == '__main__':
    unittest.main()
