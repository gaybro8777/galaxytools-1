#!/usr/bin/env python

from __future__ import print_function

import json
import optparse
import os.path
import sys

from load_db import create_table

from query_db import describe_tables, get_connection, run_query


"""
JSON config:
{ tables : [
    { file_path : '/home/galaxy/dataset_101.dat',
            table_name : 't1',
            column_names : ['c1','c2','c3'],
            pkey_autoincr : 'id'
            comment_lines : 1
            unique: ['c1'],
            index: ['c2', 'c3']
    },
    { file_path : '/home/galaxy/dataset_102.dat',
            table_name : 'gff',
            column_names : ['seqname',,'date','start','end']
            comment_lines : 1
            load_named_columns : True
            filters : [{'filter': 'regex', 'pattern': '#peptide',
                        'action': 'exclude_match'},
                       {'filter': 'replace', 'column': 3,
                        'replace': 'gi[|]', 'pattern': ''}]
    },
    { file_path : '/home/galaxy/dataset_103.dat',
            table_name : 'test',
            column_names : ['c1', 'c2', 'c3']
    }
    ]
}
"""


def __main__():
    # Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option('-s', '--sqlitedb', dest='sqlitedb', default=None,
                      help='The SQLite Database')
    parser.add_option('-j', '--jsonfile', dest='jsonfile', default=None,
                      help='JSON dict of table specifications')
    parser.add_option('-q', '--query', dest='query', default=None,
                      help='SQL query')
    parser.add_option('-Q', '--query_file', dest='query_file', default=None,
                      help='SQL query file')
    parser.add_option('-n', '--no_header', dest='no_header', default=False,
                      action='store_true',
                      help='Include a column headers line')
    parser.add_option('-o', '--output', dest='output', default=None,
                      help='Output file for query results')
    (options, args) = parser.parse_args()

    # determine output destination
    if options.output is not None:
        try:
            outputPath = os.path.abspath(options.output)
            outputFile = open(outputPath, 'w')
        except Exception as e:
            exit('Error: %s' % (e))
    else:
        outputFile = sys.stdout

    def _create_table(ti, table):
        path = table['file_path']
        table_name =\
            table['table_name'] if 'table_name' in table else 't%d' % (ti + 1)
        comment_lines =\
            table['comment_lines'] if 'comment_lines' in table else 0
        comment_char =\
            table['comment_char'] if 'comment_char' in table else None
        column_names =\
            table['column_names'] if 'column_names' in table else None
        if column_names:
            load_named_columns =\
                table['load_named_columns']\
                if 'load_named_columns' in table else False
        else:
            load_named_columns = False
        unique_indexes = table['unique'] if 'unique' in table else []
        indexes = table['index'] if 'index' in table else []
        filters = table['filters'] if 'filters' in table else None
        pkey_autoincr = \
            table['pkey_autoincr'] if 'pkey_autoincr' in table else None
        create_table(get_connection(options.sqlitedb), path, table_name,
                     pkey_autoincr=pkey_autoincr,
                     column_names=column_names,
                     skip=comment_lines,
                     comment_char=comment_char,
                     load_named_columns=load_named_columns,
                     filters=filters,
                     unique_indexes=unique_indexes,
                     indexes=indexes)

    if options.jsonfile:
        try:
            fh = open(options.jsonfile)
            tdef = json.load(fh)
            if 'tables' in tdef:
                for ti, table in enumerate(tdef['tables']):
                    _create_table(ti, table)
        except Exception as e:
            exit('Error: %s' % (e))

    query = None
    if (options.query_file is not None):
        with open(options.query_file, 'r') as fh:
            query = ''
            for line in fh:
                query += line
    elif (options.query is not None):
        query = options.query

    if (query is None):
        try:
            describe_tables(get_connection(options.sqlitedb), outputFile)
        except Exception as e:
            exit('Error: %s' % (e))
    else:
        try:
            run_query(get_connection(options.sqlitedb), query, outputFile,
                      no_header=options.no_header)
        except Exception as e:
            exit('Error: %s' % (e))


if __name__ == "__main__":
    __main__()
