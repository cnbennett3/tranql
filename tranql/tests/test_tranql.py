import json
import pytest
import os
import itertools
import requests
from pprint import pprint
from deepdiff import DeepDiff
from tranql.main import TranQL
from tranql.main import TranQLParser, set_verbose
from tranql.tranql_ast import SetStatement, SelectStatement
from tranql.tests.util import assert_lists_equal, set_mock, ordered
from tranql.tests.mocks import MockHelper
from tranql.tests.mocks import MockMap
#set_verbose ()

def assert_parse_tree (code, expected):
    """ Parse a block of code into a parse tree. Then assert the equality
    of that parse tree to a list of expected tokens. """
    tranql = TranQL ()
    tranql.resolve_names = False
    actual = tranql.parser.parse (code).parse_tree
    #print (f"{actual}")
    assert_lists_equal (
        actual,
        expected)

#####################################################
#
# Parser tests. Verify we produce the AST for the
# expected grammar correctly.
#
#####################################################

def test_parse_predicate (requests_mock):
    set_mock(requests_mock, "predicates")

    """ Test parsing a predicate. """
    print (f"test_parse_predicate()")
    assert_parse_tree (
        code = """
        SELECT chemical_substance-[treats]->disease
          FROM "/graph/gamma/quick"
          WHERE chemical_substance='PUBCHEM:2083'
            SET "$.knowledge_graph.nodes.[*].id as indications
        """,
        expected = [
            [ [ "select",
                "chemical_substance",
                [ "-[",
                  "treats",
                  "]->"
                ], "disease", "\n"
            ],
            "          ",
            [ "from", [ "/graph/gamma/quick"] ],
            ["where",
             [
                 "chemical_substance",
                 "=",
                 "PUBCHEM:2083"
             ]
            ], [ "" ]
            ]])

def test_parse_set (requests_mock):
    set_mock(requests_mock, "workflow-5")

    """ Test parsing set statements. """
    print (f"test_parse_set()")
    assert_parse_tree (
        code = """
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/' """,
        expected = [
            ["set", "disease", "=", "asthma"],
            ["set", "max_p_value", "=", "0.5"],
            ["set", "cohort", "=", "COHORT:22"],
            ["set", "population_density", "=", 2],
            ["set", "icees.population_density_cluster", "=", "http://localhost/ICEESQuery"],
            ["set", "gamma.quick", "=", "http://robokop.renci.org:80/api/simple/quick/"]
        ])

def test_parse_set_with_comment (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test parsing set statements with comments. """
    print (f"test_parse_set_with_comment()")
    assert_parse_tree (
        code = """
        -- This is a comment
        SET disease = 'asthma' """,
        expected = [
            ["set", "disease", "=", "asthma"]
        ])

def test_parse_select_simple (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the token stream of a simple select statement. """
    print (f"test_parse_select_simple()")
    assert_parse_tree (
        code = """
        SELECT chemical_substance->gene->biological_process->phenotypic_feature
          FROM "/graph/gamma/quick"
         WHERE chemical_substance = $chemical_exposures
           SET knowledge_graph """,
        expected = [
            [["select", "chemical_substance", "->", "gene", "->", "biological_process", "->", "phenotypic_feature", "\n"],
             "          ",
             ["from", ["/graph/gamma/quick"]],
             ["where", ["chemical_substance", "=", "$chemical_exposures"]],
             ["set", ["knowledge_graph"]]]
        ])

def test_parse_select_complex (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the token stream of a more complex select statement. """
    print (f"test_parse_select_complex()")
    assert_parse_tree (
        code = """
        SELECT disease->chemical_substance
          FROM "/flow/5/mod_1_4/icees/by_residential_density"
         WHERE disease = "asthma"
           AND EstResidentialDensity < "2"
           AND cohort = "COHORT:22"
           AND max_p_value = "0.5"
           SET '$.nodes.[*].id' AS chemical_exposures """,
        expected = [
            [["select", "disease", "->", "chemical_substance", "\n"],
             "          ",
             ["from", ["/flow/5/mod_1_4/icees/by_residential_density"]],
             ["where",
              ["disease", "=", "asthma"], "and",
              ["EstResidentialDensity", "<", "2"], "and",
              ["cohort", "=", "COHORT:22"], "and",
              ["max_p_value", "=", "0.5"]
             ],
             ["set", ["$.nodes.[*].id", "as", "chemical_exposures"]]]
        ])

def test_parse_query_with_repeated_concept (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Verify the parser accepts a grammar allowing concept names to be prefixed by a name
    and a colon. """
    print (f"test_parse_query_with_repeated_concept")
    assert_parse_tree (
        code="""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'asthma'
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
        """,
        expected = [
            [["select", "cohort_diagnosis:disease","->","diagnoses:disease","\n"],
             "  ",
             ["from",
              ["/clinical/cohort/disease_to_chemical_exposure"]
             ],
             ["where",
              ["cohort_diagnosis","=","asthma"],
              "and",
              ["Sex","=","0"],
              "and",
              ["cohort","=","all_patients"],
              "and",
              ["max_p_value","=","0.5"]
             ],
             ["set",
              ["$.knowledge_graph.nodes.[*].id","as","diagnoses"]
             ]
            ]])

#####################################################
#
# AST tests. Test abstract syntax tree components.
#
#####################################################
def test_ast_set_variable (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test setting a varaible to an explicit value. """
    print ("test_ast_set_variable ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value="x")
    statement.execute (tranql)
    assert tranql.context.resolve_arg ("$variable") == 'x'
def test_ast_set_graph (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Set a variable to a graph passed as a result. """
    print ("test_ast_set_graph ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value=None, jsonpath_query=None)
    statement.execute (tranql, context={ 'result' : { "a" : 1 } })
    assert tranql.context.resolve_arg ("$variable")['a'] == 1
def test_ast_set_graph (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Set a variable to the value returned by executing a JSONPath query. """
    print ("test_ast_set_graph ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    statement = SetStatement (variable="variable", value=None, jsonpath_query="$.nodes.[*]")
    statement.execute (tranql, context={
        'result' : {
            "nodes" : [ {
                "id" : "x:y"
            } ]
        }
    })
    assert tranql.context.resolve_arg ("$variable")[0]['id'] == "x:y"
def test_ast_generate_questions (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
           -- named query concepts work.
           -- the question graph is build incorporating where clause constraints.
    """
    print ("test_ast_set_generate_questions ()")
    app = TranQL ()
    app.resolve_names = False
    ast = app.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)
    questions = ast.statements[0].generate_questions (app)
    assert questions[0]['question_graph']['nodes'][0]['curie'] == 'MONDO:0004979'
    assert questions[0]['question_graph']['nodes'][0]['type'] == 'disease'
def test_ast_format_constraints (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- The syntax to pass values to reasoners in the where clause (e.g. "icees.foo = bar") functions properly
    """
    print("test_ast_format_constraints ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT population_of_individual_organisms->chemical_substance
          FROM "/clinical/cohort/disease_to_chemical_exposure"
         WHERE icees.should_format = 1
           AND robokop.should_not_format = 0
    """)
    select = ast.statements[0]
    select.format_constraints(tranql)
    print(select.where)
    assert_lists_equal(select.where, [
        ['should_format', '=', 1],
        ['should_format', '=', 1],
        ['robokop.should_not_format', '=', 0],
        ['robokop.should_not_format', '=', 0]
    ])
def test_ast_backwards_arrow (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print("test_ast_backwards_arrow ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT gene->biological_process<-microRNA
          FROM "/schema"
    """)
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))
    backwards_questions = statements[1].generate_questions(tranql)

    assert len(backwards_questions) == 1
    assert len(backwards_questions[0]["question_graph"]["edges"]) == 1
    assert backwards_questions[0]["question_graph"]["edges"][0]["source_id"] == "microRNA"
    assert backwards_questions[0]["question_graph"]["edges"][0]["target_id"] == "biological_process"
def test_ast_decorate_element (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- The SelectStatement::decorate method properly decorates both nodes and edges
    """
    print("test_ast_decorate_element ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT chemical_substance->disease
          FROM "/graph/gamma/quick"
    """)
    select = ast.statements[0]
    node = {
        "id": "CHEBI:36314",
        "name": "glycerophosphoethanolamine",
        "omnicorp_article_count": 288,
        "type": "chemical_substance"
    }
    edge = {
        "ctime": [
            1544077522.7678425
        ],
        "edge_source": [
            "chembio.graph_pubchem_to_ncbigene"
        ],
        "id": "df662e2842d44fa2c0b5d945044317e3",
        "predicate_id": "SIO:000203",
        "publications": [
            "PMID:16217747"
        ],
        "relation": [
            "CTD:interacts_with"
        ],
        "relation_label": [
            "interacts"
        ],
        "source_id": "CHEBI:36314",
        "target_id": "HGNC:8971",
        "type": "directly_interacts_with",
        "weight": 0.4071474314830641
    }
    select.decorate(node,True,{
        "schema" : select.get_schema_name(tranql)
    })
    select.decorate(edge,False,{
        "schema" : select.get_schema_name(tranql)
    })

    assert_lists_equal(node["reasoner"],["robokop"])

    assert_lists_equal(edge["reasoner"],["robokop"])
    assert_lists_equal(edge["source_database"],["unknown"])
def test_ast_resolve_name (requests_mock):
    set_mock(requests_mock, "resolve_name")
    """ Validate that
            -- The SelectStatement::resolve_name method will correctly retrieve equivalent identifiers from a given name
    """
    print("test_ast_resolve_name ()")
    assert_lists_equal(SelectStatement.resolve_name("ibuprofen","chemical_substance"),[
        'CHEBI:132922',
        'CHEBI:5855',
        'CHEBI:43415',
        'PUBCHEM:3672',
        'MESH:D007052',
        'CHEBI:5855',
        'CHEMBL:CHEMBL521']
    )
def test_ast_predicate_question (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- A query with a predicate will be properly formatted into a question graph
    """
    print("test_ast_predicates ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT chemical_substance-[treats]->disease
          FROM "/graph/gamma/quick"
         WHERE chemical_substance='CHEMBL:CHEMBL521'
    """)
    select = ast.statements[0]
    question = select.generate_questions(tranql)[0]["question_graph"]

    assert len(question["edges"]) == 1

    assert "type" in question["edges"][0]
    assert question["edges"][0]["type"] == "treats"
def test_ast_multiple_reasoners (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- A query spanning multiple reasoners will query multiple reasoners.
            -- A transitions that multiple reasoners support will query each reasoner that supports it.
    """
    print("test_ast_multiple_reasoners ()")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT chemical_substance->disease->gene
          FROM "/schema"
    """)
    # RTX and Robokop both support transitions between chemical_substance->disease and only Robokop supports transitions between disease->gene
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))
    assert_lists_equal(statements[0].query.order,['chemical_substance','disease'])
    assert statements[0].get_schema_name(tranql) == "robokop"

    assert_lists_equal(statements[1].query.order,['chemical_substance','disease'])
    assert statements[1].get_schema_name(tranql) == "rtx"

    assert_lists_equal(statements[2].query.order,['disease','gene'])
    assert statements[2].get_schema_name(tranql) == "robokop"
def test_ast_merge_knowledge_maps (requests_mock):
    set_mock(requests_mock, "workflow-5")
    tranql = TranQL ()
    tranql.asynchronous = False
    tranql.resolve_names = False
    ast = tranql.parse ("""
        select chemical_substance->disease->gene
          from "/schema"
         where chemical_substance="CHEMBL:CHEMBL3"
    """)

    # select = ast.statements[0]
    # statements = select.plan (select.planner.plan (select.query))
    # print(statements[0].query.order)

    # (select.execute_plan(tranql))

    responses = [
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                    'chemical_substance' : 'CHEBI:100',
                        'disease' : 'MONDO:50'
                    },
                    'edge_bindings' : {
                        'e0' : 'ROOT_EDGE'
                    }
                }
            ],
            'question_order' : ['chemical_substance','disease']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'disease' : 'MONDO:50',
                        'gene' : 'HGNC:1',
                        'metabolite' : 'KEGG:C00017'
                    },
                    'edge_bindings' : {
                        'e1' : 'TEST_EDGE'
                    }
                }
            ],
            'question_order' : ['disease','gene','metabolite']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'disease' : 'MONDO:50',
                        'gene' : 'HGNC:1',
                        'metabolite' : 'KEGG:FOOBAR'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['disease','gene','metabolite']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'metabolite' : 'KEGG:FOOBAR',
                        'protein' : 'UniProtKB:TESTING'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['metabolite','protein']
        },
        {
            'knowledge_map' : [
                {
                    'node_bindings' : {
                        'metabolite' : 'KEGG:C00017',
                        'protein' : 'UniProtKB:Q9NZJ5'
                    },
                    'edge_bindings' : {

                    }
                }
            ],
            'question_order' : ['metabolite','protein']
        }
    ]

    merged = SelectStatement.connect_knowledge_maps(responses,[
        'chemical_substance',
        'disease',
        'gene',
        'metabolite',
        'protein'
    ])

    assert_lists_equal(ordered(merged), ordered([
        {
            "node_bindings" : {
                "chemical_substance" : "CHEBI:100",
                "disease" : "MONDO:50",
                "gene" : "HGNC:1",
                "metabolite" : "KEGG:FOOBAR",
                "protein" : "UniProtKB:TESTING"
            },
            "edge_bindings" : {
                "e0" : "ROOT_EDGE"
            }
        },
        {
            "node_bindings" : {
                "chemical_substance" : "CHEBI:100",
                "disease" : "MONDO:50",
                "gene" : "HGNC:1",
                "metabolite" : "KEGG:C00017",
                "protein" : "UniProtKB:Q9NZJ5"
            },
            "edge_bindings" : {
                "e0" : "ROOT_EDGE",
                "e1" : "TEST_EDGE",
            }
        }
    ]))

    # print(json.dumps(merged,indent=2))

def test_ast_merge_results (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that
            -- Results from the query plan are being merged together correctly
    """
    print("test_ast_merge_answers ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/clinical/cohort/disease_to_chemical_exposure'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)

    select = ast.statements[0]

    # What is the proper format for the name of a mock file? This should be made into one
    mock_responses = [
        {
            'knowledge_graph': {
                'nodes': [
                    {'id': 'CHEBI:28177', 'type': 'chemical_substance'},
                    {'id': 'HGNC:2597', 'type': 'gene'},
                    {
                        'id': 'egg',
                        'name':'test_name_merge',
                        'type': 'foo_type',
                        'test_attr': ['a','b']
                    },
                    {
                        'id': 'equivalent_identifier_merge',
                        'equivalent_identifiers': ['TEST:00000'],
                        'merged_property': [
                            'a',
                            'b'
                        ]
                    }
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'CHEBI:28177', 'target_id': 'HGNC:2597'},
                    {
                        # Test if edges that are connected to merged nodes will be successfully merged with other duplicate edges
                        'source_id' : 'CHEBI:28177',
                        'target_id' : 'egg',
                        'type': ['merge_this'],
                        'merge_this_list' : ['edge_1'],
                        'unique_attr_e_1' : 'e_1',
                        'id' : 'winning_edge_id'
                    },
                ]
            },
            'knowledge_map': [
                {
                    'node_bindings': {
                        'chemical_substance': 'CHEBI:28177',
                        'gene': 'HGNC:2597'
                    },
                    'edge_bindings': {}
                }
            ]
        },
        {
            'knowledge_graph': {
                'nodes': [
                    {'id': 'CHEBI:28177', 'type': 'chemical_substance'},
                    {
                        'id': 'also_test_array_type_and_string_type_merge',
                        'name':'test_name_merge',
                        'type': ['foo_type','bar_type'],
                        'test_attr': ['a','c']
                    },
                    {'id': 'TEST:00000', 'type': 'test', 'merged_property': ['a','c']},
                ],
                'edges': [
                    {'id': 'e0', 'source_id': 'CHEBI:28177', 'target_id': 'TEST:00000'},
                    {
                        'source_id' : 'CHEBI:28177',
                        'target_id' : 'also_test_array_type_and_string_type_merge',
                        'type': ['merge_this'],
                        'merge_this_list' : ['edge_2'],
                        'unique_attr_e_2' : 'e_2'
                    }
                ]
            },
            'knowledge_map': [
                {
                    'node_bindings': {
                        'chemical_substance': 'CHEBI:28177',
                        'test': 'TEST:00000'
                    },
                    'edge_bindings': {}
                }
            ]
        }
    ]

    expected_result = {
        "knowledge_graph": {
            "edges": [
                {
                    "id": "e0",
                    "source_id": "CHEBI:28177",
                    "target_id": "HGNC:2597",
                    "type": []
                },
                {
                    "id": "e0",
                    "source_id": "CHEBI:28177",
                    "target_id": "equivalent_identifier_merge",
                    "type": []
                },
                {
                    "id" : "winning_edge_id",
                    "source_id" : "CHEBI:28177",
                    "target_id" : "egg",
                    "type" : ["merge_this"],
                    "merge_this_list" : ["edge_1", "edge_2"],
                    "unique_attr_e_1" : "e_1",
                    "unique_attr_e_2" : "e_2"
                }
            ],
            "nodes": [
                {
                    "equivalent_identifiers": [
                        "CHEBI:28177"
                    ],
                    "id": "CHEBI:28177",
                    "type": ["chemical_substance"]
                },
                {
                    "equivalent_identifiers": [
                        "HGNC:2597"
                    ],
                    "id": "HGNC:2597",
                    "type": ["gene"]
                },
                {
                    "equivalent_identifiers": [
                        "also_test_array_type_and_string_type_merge",
                        "egg"
                    ],
                    "type": [
                        "foo_type",
                        "bar_type"
                    ],
                    "id": "egg",
                    "name": "test_name_merge",
                    "test_attr": [
                        "a",
                        "b",
                        "c"
                    ]
                },
                {
                    "equivalent_identifiers": [
                        "TEST:00000",
                        "equivalent_identifier_merge"
                    ],
                    "merged_property": ["a", "b", "c"],
                    "id": "equivalent_identifier_merge",
                    "type": ["test"]
                }
            ]
        },
        "knowledge_map": [
            {
                "edge_bindings": {},
                "node_bindings": {
                    "chemical_substance": "CHEBI:28177",
                    "gene": "HGNC:2597"
                }
            },
            {
                "edge_bindings": {},
                "node_bindings": {
                    "chemical_substance": "CHEBI:28177",
                    "test": "equivalent_identifier_merge"
                }
            }
        ],
        'question_graph': {
            'edges': [
                {
                    'id': 'foo',
                    'type': 'test'
                }
            ],
            'nodes': [
                {
                    'id': 'bar',
                    'type': 'bartest'
                }
            ]
        }
    }
    merged_results = select.merge_results (
        mock_responses,
        tranql,
        {
            'edges': [
                {
                    'id': 'foo',
                    'type': 'test'
                }
            ],
            'nodes': [
                {
                    'id': 'bar',
                    'type': 'bartest'
                }
            ]
        },
        root_order=None
    )
    assert ordered(merged_results) == ordered(expected_result)
def test_ast_plan_strategy (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print ("test_ast_plan_strategy ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    # QueryPlanStrategy always uses /schema regardless of the `FROM` clause.
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/schema'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)

    select = ast.statements[0]
    plan = select.planner.plan (select.query)

    # Assert that it has planned to query both gamma and rtx
    assert (
        (plan[0][1] == "/graph/gamma/quick" and plan[1][1] == "/graph/rtx") or
        (plan[1][1] == "/graph/rtx" and plan[1][1] == "/graph/gamma/quick")
    )
    # Both should be querying the same thing (disease->diseasee), differing only in the sub_schema that they are querying
    for sub_schema_plan in plan:
        assert sub_schema_plan[2][0][0].type_name == "disease"
        assert sub_schema_plan[2][0][0].name == "cohort_diagnosis"
        assert sub_schema_plan[2][0][0].nodes == ["MONDO:0004979"]

        assert sub_schema_plan[2][0][1].direction == "->"
        assert sub_schema_plan[2][0][1].predicate == None

        assert sub_schema_plan[2][0][2].type_name == "disease"
        assert sub_schema_plan[2][0][2].name == "diagnoses"
        assert sub_schema_plan[2][0][2].nodes == []
def test_ast_implicit_conversion (requests_mock):
    set_mock(requests_mock, "workflow-5")
    tranql = TranQL ()
    ast = tranql.parse ("""
        SELECT drug_exposure->chemical_substance
         FROM '/schema'
    """)
    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))

    assert_lists_equal(statements[0].query.order,["drug_exposure","chemical_substance"])
    assert statements[0].get_schema_name(tranql) == "implicit_conversion"

def test_ast_plan_statements (requests_mock):
    set_mock(requests_mock, "workflow-5")
    print("test_ast_plan_statements ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    # QueryPlanStrategy always uses /schema regardless of the `FROM` clause.
    ast = tranql.parse ("""
        SELECT cohort_diagnosis:disease->diagnoses:disease
          FROM '/schema'
         WHERE cohort_diagnosis = 'MONDO:0004979' --asthma
           AND Sex = '0'
           AND cohort = 'all_patients'
           AND max_p_value = '0.5'
           SET '$.knowledge_graph.nodes.[*].id' AS diagnoses
    """)


    select = ast.statements[0]
    statements = select.plan (select.planner.plan (select.query))

    assert len(statements) == 2

    for statement in statements:
        assert_lists_equal(
            list(statement.query.concepts.keys()),
            [
                "cohort_diagnosis",
                "diagnoses"
            ]
        )

        assert statement.query.concepts['cohort_diagnosis'].nodes == ["MONDO:0004979"]
        assert statement.query.concepts['diagnoses'].nodes == []
        # TODO: figure out why there are duplicates generated??
        assert_lists_equal(statement.where, [
            ['cohort_diagnosis', '=', 'MONDO:0004979'],
            ['Sex', '=', '0'], ['Sex', '=', '0'],
            ['cohort', '=', 'all_patients'],
            ['cohort', '=', 'all_patients'],
            ['max_p_value', '=', '0.5'],
            ['max_p_value', '=', '0.5']
        ])
        assert statement.set_statements == []

    assert (
        (statements[0].service == "/graph/gamma/quick" and statements[1].service == "/graph/rtx") or
        (statements[0].service == "/graph/rtx" and statements[1].service == "/graph/gamma/quick")
    )

def test_ast_bidirectional_query (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Validate that we parse and generate queries correctly for bidirectional queries. """
    print ("test_ast_bidirectional_query ()")
    app = TranQL ()
    app.resolve_names = False
    disease_id = "MONDO:0004979"
    chemical = "PUBCHEM:2083"
    app.context.set ("drug", chemical)
    app.context.set ("disease", disease_id)
    mocker = MockHelper ()
    expectations = {
        "cop.tranql" : mocker.get_obj ("bidirectional_question.json")
    }
    queries = { os.path.join (os.path.dirname (__file__), "..", "queries", k) : v
                for k, v in expectations.items () }
    for program, expected_output in queries.items ():
        ast = app.parse_file (program)
        statement = ast.statements
        """ This uses an unfortunate degree of knowledge about the implementation,
        both of the AST, and of theq query. Consider alternatives. """
        questions = ast.statements[2].generate_questions (app)
        nodes = questions[0]['question_graph']['nodes']
        edges = questions[0]['question_graph']['edges']
        node_index = { n['id'] : i for i, n in enumerate (nodes) }
        assert nodes[-1]['curie'] == disease_id
        assert nodes[0]['curie'] == chemical
        assert node_index[edges[-1]['target_id']] == node_index[edges[-1]['source_id']] - 1

#####################################################
#
# Interpreter tests. Test the interpreter interface.
#
#####################################################
def test_interpreter_set (requests_mock):
    set_mock(requests_mock, "workflow-5")
    """ Test set statements by executing a few and checking values after. """
    print ("test_interpreter_set ()")
    tranql = TranQL ()
    tranql.resolve_names = False
    tranql.execute ("""
        -- Test set statements.
        SET disease = 'asthma'
        SET max_p_value = '0.5'
        SET cohort = 'COHORT:22'
        SET population_density = 2
        SET icees.population_density_cluster = 'http://localhost/ICEESQuery'
        SET gamma.quick = 'http://robokop.renci.org:80/api/simple/quick/' """)

    variables = [ "disease", "max_p_value", "cohort", "icees.population_density_cluster", "gamma.quick" ]
    output = { k : tranql.context.resolve_arg (f"${k}") for k in variables }
    #print (f"resolved variables --> {json.dumps(output, indent=2)}")
    assert output['disease'] == "asthma"
    assert output['cohort'] == "COHORT:22"

def test_program (requests_mock):
    print ("test_program ()")
    mock_map = MockMap (requests_mock, "workflow-5")
    tranql = TranQL (options = {
        "asynchronous" : False,
        "resolve_names" : False
    })
    ast = tranql.execute ("""
    --
    -- Workflow 5
    --
    --   Modules 1-4: Chemical Exposures by Clinical Clusters
    --      For sub-clusters within the overall ICEES asthma cohort defined by
    --      differential population density, which chemicals are related to these
    --      clusters with a p_value less than some threshold?
    --
    --   Modules 5-*: Knowledge Graph Phenotypic Associations
    --      For chemicals produced by the first steps, what phenotypes are
    --      associated with exposure to these chemicals?
    --
    SET id_filters = "SCTID,rxcui,CAS,SMILES,umlscui"

    SELECT population_of_individual_organisms->drug_exposure
      FROM "/clinical/cohort/disease_to_chemical_exposure"
     WHERE EstResidentialDensity < '2'
       AND population_of_individual_organizms = 'x'
       AND cohort = 'all_patients'
       AND max_p_value = '0.1'
       SET '$.knowledge_graph.nodes.[*].id' AS chemical_exposures

    SELECT chemical_substance->gene->biological_process->phenotypic_feature
      FROM "/graph/gamma/quick"
     WHERE chemical_substance = $chemical_exposures
       SET knowledge_graph
    """)

    #print (f"{ast}")
    expos = tranql.context.resolve_arg("$chemical_exposures")
    #print (f" expos =======> {json.dumps(expos)}")

    kg = tranql.context.resolve_arg("$knowledge_graph")
    assert kg['knowledge_graph']['nodes'][0]['id'] == "CHEBI:28177"
    assert kg['knowledge_map'][0]['node_bindings']['chemical_substance'] == "CHEBI:28177"
