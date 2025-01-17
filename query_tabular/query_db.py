#!/usr/bin/env python

from __future__ import print_function

import re
import sqlite3 as sqlite
import sys


TABLE_QUERY = \
    """
    SELECT name, sql
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """


def regex_match(expr, item):
    return re.match(expr, item) is not None


def regex_search(expr, item):
    return re.search(expr, item) is not None


def regex_sub(expr, replace, item):
    return re.sub(expr, replace, item)


def get_connection(sqlitedb_path, addfunctions=True):
    conn = sqlite.connect(sqlitedb_path)
    if addfunctions:
        conn.create_function("re_match", 2, regex_match)
        conn.create_function("re_search", 2, regex_search)
        conn.create_function("re_sub", 3, regex_sub)
    return conn


def describe_tables(conn, outputFile):
    try:
        c = conn.cursor()
        tables_query = TABLE_QUERY
        rslt = c.execute(tables_query).fetchall()
        for table, sql in rslt:
            print("Table %s:" % table, file=outputFile)
            try:
                col_query = 'SELECT * FROM %s LIMIT 0' % table
                cur = conn.cursor().execute(col_query)
                cols = [col[0] for col in cur.description]
                print(" Columns: %s" % cols, file=outputFile)
            except Exception as exc:
                print("Warning: %s" % exc, file=sys.stderr)
    except Exception as e:
        exit('Error: %s' % (e))
    exit(0)


def run_query(conn, query, outputFile, no_header=False):
    cur = conn.cursor()
    results = cur.execute(query)
    if not no_header:
        outputFile.write("#%s\n" % '\t'.join(
            [str(col[0]) for col in cur.description]))
        # yield [col[0] for col in cur.description]
    for i, row in enumerate(results):
        # yield [val for val in row]
        outputFile.write("%s\n" % '\t'.join(
            [str(val) if val is not None else '' for val in row]))
