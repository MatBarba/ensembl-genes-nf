#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
Annotation stats Nextflow pipeline tasks.
"""


# standard library
import pathlib

from pprint import pp as pprint

# third party
import fire
import pymysql

from tabulate import tabulate

# project


connection_configs = {
    "mysql_ens_meta_prod_1": {
        "alias": "meta1",
        "host": "mysql-ens-meta-prod-1",
        "port": 4483,
        "user": "ensro",
    },
    "mysql_ens_mirror_5": {
        "alias": "m5",
        "host": "mysql-ens-mirror-5",
        "port": 4692,
        "user": "ensro",
    },
}


def run_sql_query(
    query: str,
    mysql_server: str,
    database: str,
    debug: bool = False,
):
    """
    Run the SQL query on the specified server and database.
    """
    connection_config = connection_configs[mysql_server]

    connection = pymysql.connect(
        host=connection_config["host"],
        port=connection_config["port"],
        user=connection_config["user"],
        database=database,
    )

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            query_result = cursor.fetchall()

            columns = [column[0] for column in cursor.description]

    if debug:
        print(tabulate(query_result, headers=columns, tablefmt="psql"))
        exit()

    return (columns, query_result)


def run_sql_query_file(
    query_file: str,
    mysql_server: str,
    database: str,
    debug: bool = False,
):
    """
    Run the SQL query in query_file on the specified server and database.
    """
    with open(query_file, "r") as file:
        query = file.read()

    columns, query_result = run_sql_query(
        query=query, mysql_server=mysql_server, database=database, debug=debug
    )

    return (columns, query_result)


def get_recent_annotations(query_file: str, annotations_csv: str):
    """
    Retrieve recent annotations from the production metadata database.
    """
    database = "ensembl_metadata_qrp"
    _columns, query_result = run_sql_query_file(
        query_file=query_file, mysql_server="mysql_ens_meta_prod_1", database=database
    )

    annotation_databases = [annotation[0] for annotation in query_result]

    # save annotation databases list to a file
    with open(annotations_csv, "w") as file:
        for annotation_database in annotation_databases:
            file.write(f"{annotation_database}\n")

    # output annotation databases list to stdout
    for annotation_database in annotation_databases:
        print(annotation_database)


def get_annotation_info(annotation_database: str):
    """
    Get annotation information from the annotation core database.
    """
    # get species.scientific_name
    query = "SELECT meta_value FROM meta WHERE meta_key = 'species.scientific_name';"
    _columns, query_result = run_sql_query(
        query=query, mysql_server="mysql_ens_mirror_5", database=annotation_database
    )
    species_scientific_name = query_result[0][0]

    # get assembly.accession
    query = "SELECT meta_value FROM meta WHERE meta_key = 'assembly.accession';"
    _columns, query_result = run_sql_query(
        query=query, mysql_server="mysql_ens_mirror_5", database=annotation_database
    )
    assembly_accession = query_result[0][0]

    annotation_info = {
        "species_scientific_name": species_scientific_name,
        "assembly_accession": assembly_accession,
    }

    return annotation_info


def check_stats_files(annotation_directory: str, production_name: str):
    annotation_directory = pathlib.Path(annotation_directory)

    readme_file = annotation_directory / "statistics_README.txt"
    statistics_file = (
        annotation_directory / f"{production_name}_annotation_statistics.txt"
    )

    return readme_file.exists() and statistics_file.exists()


if __name__ == "__main__":
    try:
        fire.Fire()
    except KeyboardInterrupt:
        print("Interrupted with CTRL-C, exiting...")
