#!/bin/env python

import os
import sys
import unittest
import httplib
import traceback

import github

class RecordReplayException( Exception ):
    pass

class RecordingHttpsConnection:
    class HttpResponse( object ):
        def __init__( self, file, res ):
            self.status = res.status
            self.__headers = res.getheaders()
            self.__output = res.read()
            file.write( str( self.status ) + "\n" )
            file.write( str( self.__headers ) + "\n" )
            file.write( str( self.__output ) + "\n" )

        def getheaders( self ):
            return self.__headers

        def read( self ):
            return self.__output

    __realHttpsConnection = httplib.HTTPSConnection

    def __init__( self, file, *args, **kwds ):
        self.__file = file
        self.__cnx = self.__realHttpsConnection( *args, **kwds )

    def request( self, verb, url, input, headers ):
        print verb, url
        self.__cnx.request( verb, url, input, headers )
        del headers[ "Authorization" ] # Do not let sensitive info in git :-p
        self.__file.write( verb + " " + url + " " + str( headers ) + " " + input + "\n" )

    def getresponse( self ):
        return RecordingHttpsConnection.HttpResponse( self.__file, self.__cnx.getresponse() )

    def close( self ):
        self.__file.write( "\n" )
        return self.__cnx.close()

class ReplayingHttpsConnection:
    class HttpResponse( object ):
        def __init__( self, file ):
            self.status = int( file.readline().strip() )
            self.__headers = eval( file.readline().strip() )
            self.__output = file.readline().strip()

        def getheaders( self ):
            return self.__headers

        def read( self ):
            return self.__output

    def __init__( self, file ):
        self.__file = file

    def request( self, verb, url, input, headers ):
        del headers[ "Authorization" ]
        expectation = self.__file.readline().strip()
        while expectation.startswith( "#" ):
            self.__file.readline()
            self.__file.readline()
            self.__file.readline()
            self.__file.readline()
            expectation = self.__file.readline().strip()
        if expectation != verb + " " + url + " " + str( headers ) + " " + input:
            print "Expected [", expectation, "] but got [", verb + " " + url + " " + str( headers ) + " " + input, "]"
            raise RecordReplayException( "This test has been changed since last record. Please re-run this script with argument '--record'" )

    def getresponse( self ):
        return ReplayingHttpsConnection.HttpResponse( self.__file )

    def close( self ):
        self.__file.readline()

class TestCase( unittest.TestCase ):
    def setUp( self ):
        unittest.TestCase.setUp( self )
        self.__file = None
        httplib.HTTPSConnection = lambda *args, **kwds: ReplayingHttpsConnection( self.__openFile( "r" ) )
        self.g = github.Github( "login", "password" )

    def setUpForRecord( self ):
        import GithubCredentials
        unittest.TestCase.setUp( self )
        self.__file = None
        httplib.HTTPSConnection = lambda *args, **kwds: RecordingHttpsConnection( self.__openFile( "w" ), *args, **kwds )
        self.g = github.Github( GithubCredentials.login, GithubCredentials.password )

    def tearDown( self ):
        unittest.TestCase.tearDown( self )
        self.__file.close()

    def __openFile( self, mode ):
        for ( _, _, functionName, _ ) in traceback.extract_stack():
            if functionName.startswith( "test" ):
                fileName = os.path.join( "ReplayDataForNewIntegrationTest", self.__class__.__name__ + "." + functionName[ 4: ] + ".txt" )
        if self.__file is None:
            self.__file = open( fileName, mode )
        return self.__file

class AuthenticatedUser( TestCase ):
    def setUp( self ):
        TestCase.setUp( self )
        self.u = self.g.get_user()

    def tearDown( self ):
        TestCase.tearDown( self )

    def testAttributes( self ):
        self.assertEqual( self.u.avatar_url, "https://secure.gravatar.com/avatar/b68de5ae38616c296fa345d2b9df2225?d=https://a248.e.akamai.net/assets.github.com%2Fimages%2Fgravatars%2Fgravatar-140.png" )
        self.assertEqual( self.u.bio, "" )
        self.assertEqual( self.u.blog, "http://vincent-jacques.net" )
        self.assertEqual( self.u.collaborators, 0 )
        self.assertEqual( self.u.company, "Criteo" )
        self.assertEqual( self.u.created_at, "2010-07-09T06:10:06Z" )
        self.assertEqual( self.u.disk_usage, 16692 )
        self.assertEqual( self.u.email, "vincent@vincent-jacques.net" )
        self.assertEqual( self.u.followers, 13 )
        self.assertEqual( self.u.following, 24 )
        self.assertEqual( self.u.gravatar_id, "b68de5ae38616c296fa345d2b9df2225" )
        self.assertEqual( self.u.hireable, False )
        self.assertEqual( self.u.html_url, "https://github.com/jacquev6" )
        self.assertEqual( self.u.id, 327146 )
        self.assertEqual( self.u.location, "Paris, France" )
        self.assertEqual( self.u.login, "jacquev6" )
        self.assertEqual( self.u.name, "Vincent Jacques" )
        self.assertEqual( self.u.owned_private_repos, 5 )
        ### @todo self.assertEqual( self.u.plan, "" )
        self.assertEqual( self.u.private_gists, 5 )
        self.assertEqual( self.u.public_gists, 1 )
        self.assertEqual( self.u.public_repos, 10 )
        self.assertEqual( self.u.total_private_repos, 5 )
        self.assertEqual( self.u.type, "User" )
        self.assertEqual( self.u.url, "https://api.github.com/users/jacquev6" )

if len( sys.argv ) > 1:
    assert sys.argv[ 1 ] == "--record"
    for method in sys.argv[ 2 : ]:
        class_, method = method.split( "." )
        method = "test" + method
        print "Recording method", method, "of class", class_
        # exec "testCase = " + class_ + "()"
        testCase = AuthenticatedUser( methodName = method )
        method = getattr( testCase, method )
        TestCase.setUp = TestCase.setUpForRecord
        testCase.setUp()
        method()
        testCase.tearDown()
else:
    unittest.main()
