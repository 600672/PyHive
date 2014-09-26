"""Hive integration tests.

These rely on having a Hive+Hadoop cluster set up with HiveServer2 running.
They also require a tables created by make_test_tables.sh.
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from TCLIService import ttypes
from pyhive import hive
from pyhive.tests.dbapi_test_case import DBAPITestCase
from pyhive.tests.dbapi_test_case import with_cursor
import contextlib
import mock
import unittest

_HOST = 'localhost'


class TestHive(unittest.TestCase, DBAPITestCase):
    __test__ = True

    def connect(self):
        return hive.connect(host=_HOST, configuration={'mapred.job.tracker': 'local'})

    @with_cursor
    def test_description(self, cursor):
        cursor.execute('SELECT * FROM one_row')
        desc = [('number_of_rows', 'INT_TYPE', None, None, None, None, True)]
        self.assertEqual(cursor.description, desc)
        self.assertEqual(cursor.description, desc)

    @with_cursor
    def test_complex(self, cursor):
        cursor.execute('SELECT * FROM one_row_complex')
        # TODO Presto drops the union and decimal fields
        self.assertEqual(cursor.description, [
            ('boolean', 'BOOLEAN_TYPE', None, None, None, None, True),
            ('tinyint', 'TINYINT_TYPE', None, None, None, None, True),
            ('smallint', 'SMALLINT_TYPE', None, None, None, None, True),
            ('int', 'INT_TYPE', None, None, None, None, True),
            ('bigint', 'BIGINT_TYPE', None, None, None, None, True),
            ('float', 'FLOAT_TYPE', None, None, None, None, True),
            ('double', 'DOUBLE_TYPE', None, None, None, None, True),
            ('string', 'STRING_TYPE', None, None, None, None, True),
            ('timestamp', 'TIMESTAMP_TYPE', None, None, None, None, True),
            ('binary', 'BINARY_TYPE', None, None, None, None, True),
            ('array', 'STRING_TYPE', None, None, None, None, True),
            ('map', 'STRING_TYPE', None, None, None, None, True),
            ('struct', 'STRING_TYPE', None, None, None, None, True),
            ('union', 'STRING_TYPE', None, None, None, None, True),
            ('decimal', 'DECIMAL_TYPE', None, None, None, None, True),
        ])
        self.assertEqual(cursor.fetchall(), [[
            True,
            127,
            32767,
            2147483647,
            9223372036854775807,
            0.5,
            0.25,
            'a string',
            '1970-01-01 00:00:00.0',
            '123',
            '[1,2]',
            '{1:2,3:4}',
            '{"a":1,"b":2}',
            '{0:1}',
            '0.1',
        ]])

    def test_noops(self):
        """The DB-API specification requires that certain actions exist, even though they might not
        be applicable."""
        # Wohoo inflating coverage stats!
        with contextlib.closing(self.connect()) as connection:
            with contextlib.closing(connection.cursor()) as cursor:
                self.assertEqual(cursor.rowcount, -1)
                cursor.setinputsizes([])
                cursor.setoutputsize(1, 'blah')
                connection.commit()

    @mock.patch('TCLIService.TCLIService.Client.OpenSession')
    def test_open_failed(self, open_session):
        open_session.return_value.serverProtocolVersion = \
            ttypes.TProtocolVersion.HIVE_CLI_SERVICE_PROTOCOL_V1
        self.assertRaises(hive.OperationalError, self.connect)

    def test_escape(self):
        # Hive thrift translates newlines into multiple rows. WTF.
        bad_str = '''`~!@#$%^&*()_+-={}[]|\\;:'",./<>?\t '''
        self.run_escape_case(bad_str)

    def test_newlines(self):
        """Verify that newlines are passed through in a way that doesn't fail parsing"""
        # Hive thrift translates newlines into multiple rows. WTF.
        cursor = self.connect().cursor()
        cursor.execute(
            'SELECT %s FROM one_row',
            (' \r\n \r \n ',)
        )
        self.assertEqual(cursor.fetchall(), [[' '], [' '], [' '], [' ']])

    @with_cursor
    def test_no_result_set(self, cursor):
        cursor.execute('USE default')
        self.assertIsNone(cursor.description)
        self.assertRaises(hive.ProgrammingError, cursor.fetchone)
