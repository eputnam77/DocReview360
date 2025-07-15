## Dev Gate Results - 2025-07-13T09:55:39Z

- **mypy**: failed – see logs for 238 errors (example: `ModuleNotFoundError: 'uvicorn'`)
- **pytest**: failed – `ModuleNotFoundError: uvicorn` (5 errors during collection)
- **coverage**: not computed due to test failures


#### `pre-commit run --all-files`

`pre-commit run --all-files`

(.venv) PS C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360> pre-commit run --all-files
ruff.....................................................................Passed
black....................................................................Passed
mypy.....................................................................Failed
- hook id: mypy
- exit code: 1

tests\property\test_task198_property.py:9: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task196_property.py:9: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task195_property.py:9: error: Function is missing a type annotation  [no-untyped-def]
src\docreview360\models.py:9: error: Class cannot subclass "DeclarativeBase" (has type "Any")  [misc]
src\docreview360\cache.py:9: error: Library stubs not installed for "redis"  [import-untyped]
src\docreview360\cache.py:9: note: Hint: "python3 -m pip install types-redis"
src\docreview360\cache.py:9: note: (or run "mypy --install-types" to install all missing stub packages)
src\docreview360\cache.py:9: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
src\docreview360\cache.py:11: error: Unused "type: ignore" comment  [unused-ignore]
tests\test_plugins.py:8: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_plugins.py:11: error: Function is missing a type annotation  [no-untyped-def]
tests\test_plugins.py:14: error: Module has no attribute "register"  [attr-defined]
tests\test_plugins.py:21: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_plugins.py:21: note: Use "-> None" if function does not return a value
tests\test_plugins.py:28: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_plugins.py:28: note: Use "-> None" if function does not return a value
tests\test_plugins.py:33: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_metabase_sync.py:6: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\property\test_task71_property.py:6: error: Untyped decorator makes function "test_task71_property" untyped  [misc]
tests\property\test_task71_property.py:7: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\property\test_task63_property.py:6: error: Untyped decorator makes function "test_cache_roundtrip" untyped  [misc]
tests\property\test_task27_property.py:8: error: Function is missing a type annotation  [no-untyped-def]
src\docreview360\cli.py:12: error: Untyped decorator makes function "cli" untyped  [misc]
src\docreview360\cli.py:20: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:21: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:26: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:33: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:40: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:47: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:48: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:49: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:50: error: Untyped decorator makes function "init" untyped  [misc]
src\docreview360\cli.py:55: error: Untyped decorator makes function "init" untyped  [misc]
tests\test_task29.py:13: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task29.py:30: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task29.py:37: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\property\test_task65_property.py:6: error: Untyped decorator makes function "test_task65_property" untyped  [misc]
tests\property\test_task65_property.py:7: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
src\docreview360\metabase.py:76: error: Returning Any from function declared to return "str"  [no-any-return]
tests\test_task99.py:5: error: "task99" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task98.py:5: error: "task98" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task95.py:5: error: "task95" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task94.py:5: error: "task94" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task93.py:5: error: "task93" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task92.py:5: error: "task92" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task91.py:5: error: "task91" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task64.py:5: error: "task64" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task63.py:5: error: "task63" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task62.py:5: error: "task62" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task60.py:5: error: "task60" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task58.py:5: error: "task58" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task57.py:5: error: "task57" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task51.py:5: error: "task51" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task47.py:5: error: "task47" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task40.py:5: error: "task40" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task38.py:5: error: "task38" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task37.py:5: error: "task37" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task26.py:5: error: "task26" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task21.py:5: error: "task21" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task20.py:5: error: "task20" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task198.py:5: error: "task198" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task197.py:5: error: "task197" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task195.py:5: error: "task195" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task194.py:5: error: "task194" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task193.py:5: error: "task193" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task192.py:5: error: "task192" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task190.py:5: error: "task190" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task189.py:5: error: "task189" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task188.py:5: error: "task188" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task187.py:5: error: "task187" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task186.py:5: error: "task186" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task185.py:5: error: "task185" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task184.py:5: error: "task184" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task183.py:5: error: "task183" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task182.py:5: error: "task182" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task181.py:5: error: "task181" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task180.py:5: error: "task180" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task179.py:5: error: "task179" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task178.py:5: error: "task178" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task177.py:5: error: "task177" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task176.py:5: error: "task176" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task175.py:5: error: "task175" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task174.py:5: error: "task174" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task173.py:5: error: "task173" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task172.py:5: error: "task172" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task171.py:5: error: "task171" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task170.py:5: error: "task170" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task169.py:5: error: "task169" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task168.py:5: error: "task168" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task167.py:5: error: "task167" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task137.py:6: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task137.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task130.py:5: error: "task130" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task129.py:5: error: "task129" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task128.py:5: error: "task128" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task127.py:5: error: "task127" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task126.py:4: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task125.py:5: error: "task125" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task124.py:5: error: "task124" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task123.py:5: error: "task123" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task122.py:5: error: "task122" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task121.py:5: error: "task121" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task120.py:5: error: "task120" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task12.py:5: error: "task12" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task119.py:5: error: "task119" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task118.py:5: error: "task118" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task117.py:5: error: "task117" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task116.py:5: error: "task116" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task115.py:5: error: "task115" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task114.py:5: error: "task114" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task113.py:5: error: "task113" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task112.py:5: error: "task112" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task111.py:5: error: "task111" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task103.py:5: error: "task103" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task100.py:5: error: "task100" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task06.py:5: error: "task06" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task05.py:5: error: "task05" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task04.py:5: error: "task04" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task03.py:5: error: "task03" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_metabase_dashboards.py:5: error: Function is missing a type annotation  [no-untyped-def]
tests\test_metabase_dashboards.py:6: error: Function is missing a type annotation  [no-untyped-def]
tests\test_metabase_dashboards.py:15: error: Function is missing a type annotation  [no-untyped-def]
tests\test_metabase_dashboards.py:16: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task97_property.py:6: error: Untyped decorator makes function "test_task97_property" untyped  [misc]
tests\property\test_task96_property.py:6: error: Untyped decorator makes function "test_task96_property" untyped  [misc]
tests\property\test_task94_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task94_property.py:8: error: "task94" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task90_property.py:10: error: Untyped decorator makes function "test_task90_property" untyped  [misc]
tests\property\test_task90_property.py:11: error: Untyped decorator makes function "test_task90_property" untyped  [misc]
tests\property\test_task87_property.py:6: error: Untyped decorator makes function "test_task87_property" untyped  [misc]
tests\property\test_task86_property.py:6: error: Untyped decorator makes function "test_task86_property" untyped  [misc]
tests\property\test_task57_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task57_property.py:8: error: "task57" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task52_property.py:6: error: Untyped decorator makes function "test_task52_property" untyped  [misc]
tests\property\test_task52_property.py:7: error: Untyped decorator makes function "test_task52_property" untyped  [misc]
tests\property\test_task40_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task40_property.py:8: error: "task40" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task183_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task183_property.py:8: error: "task183" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task182_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task182_property.py:8: error: "task182" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task180_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task180_property.py:8: error: "task180" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task168_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task168_property.py:8: error: "task168" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task130_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task130_property.py:8: error: "task130" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task129_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task129_property.py:8: error: "task129" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task128_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task128_property.py:8: error: "task128" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task127_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task127_property.py:8: error: "task127" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task126_property.py:6: error: Untyped decorator makes function "test_task126_property" untyped  [misc]
tests\property\test_task125_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task125_property.py:8: error: "task125" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task05_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task05_property.py:8: error: "task05" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task04_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task04_property.py:8: error: "task04" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task149.py:5: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task148.py:5: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task147.py:8: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task147.py:15: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task147.py:22: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task145.py:7: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task145.py:10: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task145.py:18: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task143.py:5: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task143.py:11: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task143.py:20: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task142.py:6: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task142.py:12: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task141.py:4: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task140.py:4: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task140.py:7: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_task140.py:7: note: Use "-> None" if function does not return a value
tests\test_task139.py:4: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task139.py:6: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task138.py:4: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task138.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task136.py:10: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task136.py:11: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task135.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task135.py:8: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task131_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
src\docreview360\api.py:211: error: Untyped decorator makes function "list_projects_endpoint" untyped  [misc]
src\docreview360\api.py:236: error: Untyped decorator makes function "create_project_endpoint" untyped  [misc]
src\docreview360\api.py:255: error: Untyped decorator makes function "get_project_endpoint" untyped  [misc]
src\docreview360\api.py:263: error: Untyped decorator makes function "get_project_workflow_endpoint" untyped  [misc]
src\docreview360\api.py:272: error: Untyped decorator makes function "update_priority_endpoint" untyped  [misc]
src\docreview360\api.py:280: error: Untyped decorator makes function "temporary_assign_endpoint" untyped  [misc]
src\docreview360\api.py:288: error: Untyped decorator makes function "import_document_endpoint" untyped  [misc]
src\docreview360\api.py:342: error: Untyped decorator makes function "import_tiptap_endpoint" untyped  [misc]
src\docreview360\api.py:368: error: Untyped decorator makes function "list_documents_endpoint" untyped  [misc]
src\docreview360\api.py:389: error: Untyped decorator makes function "get_document_endpoint" untyped  [misc]
src\docreview360\api.py:398: error: Untyped decorator makes function "update_document_endpoint" untyped  [misc]
src\docreview360\api.py:413: error: Untyped decorator makes function "add_comment_endpoint" untyped  [misc]
src\docreview360\api.py:419: error: Untyped decorator makes function "list_comments_endpoint" untyped  [misc]
src\docreview360\api.py:425: error: Untyped decorator makes function "export_document_endpoint" untyped  [misc]
src\docreview360\api.py:445: error: Untyped decorator makes function "archive_document_endpoint" untyped  [misc]
src\docreview360\api.py:456: error: Untyped decorator makes function "list_archives_endpoint" untyped  [misc]
src\docreview360\api.py:462: error: Untyped decorator makes function "get_archive_endpoint" untyped  [misc]
src\docreview360\api.py:471: error: Untyped decorator makes function "search_documents" untyped  [misc]
src\docreview360\api.py:491: error: Untyped decorator makes function "export_search_results" untyped  [misc]
src\docreview360\api.py:507: error: Untyped decorator makes function "save_search_endpoint" untyped  [misc]
src\docreview360\api.py:513: error: Untyped decorator makes function "list_saved_searches_endpoint" untyped  [misc]
src\docreview360\api.py:519: error: Untyped decorator makes function "search_stats_endpoint" untyped  [misc]
src\docreview360\api.py:525: error: Untyped decorator makes function "ai_rewrite_endpoint" untyped  [misc]
src\docreview360\api.py:532: error: Untyped decorator makes function "ai_summarize_endpoint" untyped  [misc]
src\docreview360\api.py:539: error: Untyped decorator makes function "create_document_type" untyped  [misc]
src\docreview360\api.py:546: error: Untyped decorator makes function "get_document_types" untyped  [misc]
src\docreview360\api.py:552: error: Untyped decorator makes function "export_doc_types_endpoint" untyped  [misc]
src\docreview360\api.py:560: error: Untyped decorator makes function "import_doc_types_endpoint" untyped  [misc]
src\docreview360\api.py:571: error: Untyped decorator makes function "get_document_type_endpoint" untyped  [misc]
src\docreview360\api.py:580: error: Untyped decorator makes function "update_document_type_endpoint" untyped  [misc]
src\docreview360\api.py:591: error: Untyped decorator makes function "delete_document_type_endpoint" untyped  [misc]
src\docreview360\api.py:601: error: Untyped decorator makes function "create_workflow_endpoint" untyped  [misc]
src\docreview360\api.py:607: error: Untyped decorator makes function "get_workflow_endpoint" untyped  [misc]
src\docreview360\api.py:616: error: Untyped decorator makes function "assign_reviewer_endpoint" untyped  [misc]
src\docreview360\api.py:625: error: Untyped decorator makes function "advance_workflow_endpoint" untyped  [misc]
src\docreview360\api.py:634: error: Untyped decorator makes function "create_approval_endpoint" untyped  [misc]
src\docreview360\api.py:640: error: Untyped decorator makes function "list_approvals_endpoint" untyped  [misc]
src\docreview360\api.py:646: error: Untyped decorator makes function "get_approval_endpoint" untyped  [misc]
src\docreview360\api.py:655: error: Untyped decorator makes function "update_approval_endpoint" untyped  [misc]
src\docreview360\api.py:664: error: Untyped decorator makes function "sign_approval_endpoint" untyped  [misc]
src\docreview360\api.py:685: error: Untyped decorator makes function "sign_document" untyped  [misc]
src\docreview360\api.py:706: error: Untyped decorator makes function "complete_sign" untyped  [misc]
src\docreview360\api.py:713: error: Untyped decorator makes function "get_sign_status" untyped  [misc]
src\docreview360\api.py:720: error: Untyped decorator makes function "documenso_webhook" untyped  [misc]
src\docreview360\api.py:730: error: Untyped decorator makes function "token" untyped  [misc]
src\docreview360\api.py:742: error: Untyped decorator makes function "oidc_token" untyped  [misc]
src\docreview360\api.py:748: error: Untyped decorator makes function "read_current_user" untyped  [misc]
src\docreview360\api.py:754: error: Untyped decorator makes function "read_current_oidc_user" untyped  [misc]
src\docreview360\api.py:762: error: Untyped decorator makes function "root" untyped  [misc]
src\docreview360\api.py:770: error: Untyped decorator makes function "login" untyped  [misc]
src\docreview360\api.py:787: error: Untyped decorator makes function "dashboard" untyped  [misc]
src\docreview360\api.py:795: error: Untyped decorator makes function "admin_panel" untyped  [misc]
src\docreview360\api.py:801: error: Untyped decorator makes function "list_plugins" untyped  [misc]
src\docreview360\api.py:807: error: Untyped decorator makes function "register_plugin" untyped  [misc]
src\docreview360\api.py:817: error: Untyped decorator makes function "enable_plugin" untyped  [misc]
src\docreview360\api.py:827: error: Untyped decorator makes function "disable_plugin" untyped  [misc]
src\docreview360\api.py:837: error: Untyped decorator makes function "unregister_plugin" untyped  [misc]
src\docreview360\api.py:847: error: Untyped decorator makes function "list_logs" untyped  [misc]
src\docreview360\api.py:853: error: Untyped decorator makes function "list_audit" untyped  [misc]
src\docreview360\api.py:859: error: Untyped decorator makes function "get_summary_report" untyped  [misc]
src\docreview360\api.py:865: error: Untyped decorator makes function "get_metrics_summary" untyped  [misc]
src\docreview360\api.py:871: error: Untyped decorator makes function "get_summary_csv" untyped  [misc]
src\docreview360\api.py:877: error: Untyped decorator makes function "get_dashboard_data" untyped  [misc]
src\docreview360\api.py:883: error: Untyped decorator makes function "get_widget_counts" untyped  [misc]
src\docreview360\api.py:889: error: Untyped decorator makes function "public_status_endpoint" untyped  [misc]
src\docreview360\api.py:895: error: Untyped decorator makes function "internal_status_endpoint" untyped  [misc]
src\docreview360\api.py:901: error: Untyped decorator makes function "dashboard_stream" untyped  [misc]
src\docreview360\api.py:917: error: Untyped decorator makes function "logs_stream" untyped  [misc]
src\docreview360\api.py:929: error: Untyped decorator makes function "get_config_endpoint" untyped  [misc]
src\docreview360\api.py:938: error: Untyped decorator makes function "update_config_endpoint" untyped  [misc]
tests\test_vector_search.py:25: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_vector_search.py:28: error: Function is missing a type annotation  [no-untyped-def]
tests\test_vector_search.py:49: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_vector_search.py:52: error: Function is missing a type annotation  [no-untyped-def]
tests\test_vector_search.py:66: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_vector_search.py:67: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_vector_search.py:73: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_vector_search.py:88: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_vector_search.py:89: error: Missing type parameters for generic type "tuple"  [type-arg]
tests\test_vector_search.py:90: error: Missing type parameters for generic type "tuple"  [type-arg]
tests\test_vector_search.py:92: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_vector_search.py:97: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_vector_search.py:108: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_token_env.py:7: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task46.py:30: error: Untyped decorator makes function "edit_route" untyped  [misc]
tests\test_task13.py:13: error: Item "None" of "ProjectModel | None" has no attribute "priority"  [union-attr]
tests\test_task13.py:18: error: Item "None" of "ProjectModel | None" has no attribute "temp_user"  [union-attr]
tests\test_task13.py:19: error: Item "None" of "ProjectModel | None" has no attribute "user"  [union-attr]
tests\test_task13.py:24: error: Item "None" of "ProjectModel | None" has no attribute "temp_user"  [union-attr]
tests\test_task13.py:26: error: Item "None" of "ProjectModel | None" has no attribute "temp_until"  [union-attr]
tests\test_task13.py:28: error: Item "None" of "ProjectModel | None" has no attribute "temp_user"  [union-attr]
tests\test_task13.py:29: error: Item "None" of "ProjectModel | None" has no attribute "user"  [union-attr]
tests\test_search.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_search.py:83: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_search.py:86: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_search.py:89: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_search.py:104: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_search.py:114: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_search.py:118: error: Call to untyped function "_doc_ids" in typed context  [no-untyped-call]
tests\test_plugin_api.py:11: error: Function is missing a type annotation  [no-untyped-def]
tests\test_plugin_api.py:14: error: Module has no attribute "register"  [attr-defined]
tests\test_plugin_api.py:19: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_plugin_api.py:19: note: Use "-> None" if function does not return a value
tests\test_pandiff.py:7: error: Argument 1 to "compute_diff" has incompatible type "int"; expected "str"  [arg-type]
tests\test_flower.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_flower.py:11: error: Function is missing a type annotation  [no-untyped-def]
tests\test_flower.py:14: error: Module "docreview360.flower" does not explicitly export attribute "asyncio"  [attr-defined]
tests\test_flower.py:15: error: Module "docreview360.flower" does not explicitly export attribute "asyncio"  [attr-defined]
tests\test_flower.py:24: error: Function is missing a type annotation  [no-untyped-def]
tests\test_flower.py:28: error: Function is missing a type annotation  [no-untyped-def]
tests\test_flower.py:31: error: Module "docreview360.flower" does not explicitly export attribute "asyncio"  [attr-defined]
tests\test_flower.py:32: error: Module "docreview360.flower" does not explicitly export attribute "asyncio"  [attr-defined]
tests\test_flower.py:39: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_flower.py:39: note: Use "-> None" if function does not return a value
tests\test_feature_flags.py:6: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_feature_flags.py:12: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_feature_flags.py:16: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_feature_flags.py:28: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_documenso_extra.py:17: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_documenso_extra.py:18: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_config_endpoints.py:7: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_ai_assist.py:7: error: Untyped decorator makes function "test_ai_rewrite_endpoint" untyped  [misc]
tests\test_ai_assist.py:8: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_ai_assist.py:21: error: Untyped decorator makes function "test_ai_summarize_endpoint" untyped  [misc]
tests\test_ai_assist.py:22: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_ai_assist.py:35: error: Untyped decorator makes function "test_call_openai_fallback" untyped  [misc]
tests\test_ai_assist.py:41: error: Untyped decorator makes function "test_rewrite_validation" untyped  [misc]
tests\test_ai_assist.py:47: error: Untyped decorator makes function "test_summarize_validation" untyped  [misc]
tests\test_ai_assist.py:54: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:59: error: Missing type parameters for generic type "dict"  [type-arg]
tests\test_ai_assist.py:63: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_ai_assist.py:66: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:69: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:73: error: Module "docreview360.ai_assist" does not explicitly export attribute "httpx"  [attr-defined]
tests\test_ai_assist.py:80: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:82: error: Function is missing a return type annotation  [no-untyped-def]
tests\test_ai_assist.py:85: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:88: error: Function is missing a type annotation  [no-untyped-def]
tests\test_ai_assist.py:89: error: Module "docreview360.ai_assist" does not explicitly export attribute "httpx"  [attr-defined]
tests\test_ai_assist.py:92: error: Module "docreview360.ai_assist" does not explicitly export attribute "httpx"  [attr-defined]
tests\e2e\test_workflow_e2e.py:11: error: Untyped decorator makes function "live_server" untyped  [misc]
tests\e2e\test_workflow_e2e.py:25: error: Untyped decorator makes function "test_workflow_end_to_end" untyped  [misc]
tests\e2e\test_login_e2e.py:11: error: Untyped decorator makes function "live_server" untyped  [misc]
tests\e2e\test_login_e2e.py:26: error: Untyped decorator makes function "test_login_flow" untyped  [misc]
tests\e2e\test_cli_config_e2e.py:15: error: Untyped decorator makes function "config_file" untyped  [misc]
tests\e2e\test_cli_config_e2e.py:16: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\e2e\test_cli_config_e2e.py:41: error: Returning Any from function declared to return "Path"  [no-any-return]
tests\e2e\test_cli_config_e2e.py:44: error: Untyped decorator makes function "live_server" untyped  [misc]
tests\e2e\test_cli_config_e2e.py:61: error: Untyped decorator makes function "test_cli_init_and_config" untyped  [misc]
tests\e2e\steps\common_steps.py:10: error: Function is missing a return type annotation  [no-untyped-def]
tests\e2e\steps\common_steps.py:15: error: Function is missing a type annotation  [no-untyped-def]
tests\e2e\steps\common_steps.py:20: error: Function is missing a type annotation  [no-untyped-def]
tests\e2e\steps\common_steps.py:26: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task54.py:5: error: "task54" does not return a value (it only ever returns None)  [func-returns-value]
tests\test_task30.py:9: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
tests\test_task30.py:10: error: Function is missing a return type annotation  [no-untyped-def]
tests\property\test_task54_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\property\test_task54_property.py:8: error: "task54" does not return a value (it only ever returns None)  [func-returns-value]
tests\property\test_task41_property.py:7: error: Function is missing a type annotation  [no-untyped-def]
tests\test_task146.py:6: error: Function is missing a type annotation for one or more arguments  [no-untyped-def]
Found 338 errors in 150 files (checked 560 source files)

bandit...................................................................Passed
pip-audit................................................................Passed
semgrep..................................................................Passed
pytest...................................................................



tests/test_task79.py: 1 warning
tests/test_task80.py: 2 warnings
tests/test_task81.py: 1 warning
tests/test_task82.py: 1 warning
tests/test_task83.py: 3 warnings
tests/test_task84.py: 3 warnings
tests/test_task85.py: 1 warning
tests/test_task86.py: 1 warning
tests/test_task87.py: 1 warning
tests/test_task88.py: 4 warnings
tests/test_task89.py: 1 warning
tests/test_task90.py: 1 warning
tests/test_task91.py: 1 warning
tests/test_task92.py: 1 warning
tests/test_task93.py: 1 warning
tests/test_task94.py: 1 warning
tests/test_task95.py: 1 warning
tests/test_task98.py: 1 warning
tests/test_task99.py: 1 warning
tests/test_token.py: 1 warning
tests/test_workflows.py: 1 warning
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\logs.py:59: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    entry = LogEntry(timestamp=datetime.utcnow(), action=action, user=user, metadata=metadata)

tests/property/test_task41_property.py: 1 warning
tests/test_api.py: 1 warning
tests/test_backup_panel.py: 1 warning
tests/test_backup_utils.py: 1 warning
tests/test_documenso_dashboard.py: 1 warning
tests/test_documenso_webhook.py: 1 warning
tests/test_documents.py: 2 warnings
tests/test_export.py: 1 warning
tests/test_logging.py: 1 warning
tests/test_numbering.py: 1 warning
tests/test_reporting.py: 1 warning
tests/test_search.py: 5 warnings
tests/test_signature.py: 1 warning
tests/test_status_helpers.py: 1 warning
tests/test_task17.py: 1 warning
tests/test_task34.py: 1 warning
tests/test_task41.py: 1 warning
tests/test_task49.py: 1 warning
tests/test_task66.py: 2 warnings
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\documents.py:91: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    date=datetime.utcnow(),

tests/property/test_task52_property.py::test_task52_property
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\hypothesis\internal\cache.py:87: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001BF8D3BF970>
    @property
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_ai_assist.py: 7 warnings
tests/test_flower.py: 3 warnings
tests/test_task135.py: 1 warning
tests/test_task136.py: 1 warning
tests/test_task137.py: 1 warning
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\pytest_asyncio\plugin.py:880: RuntimeWarning: Error cleaning up asyncio loop: Cannot run the event loop while another loop is running
    warnings.warn(f"Error cleaning up asyncio loop: {e}", RuntimeWarning)

tests/test_ai_assist.py: 7 warnings
tests/test_flower.py: 3 warnings
tests/test_task135.py: 1 warning
tests/test_task136.py: 1 warning
tests/test_task137.py: 1 warning
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\pytest_asyncio\plugin.py:880: RuntimeWarning: coroutine 'BaseEventLoop.shutdown_asyncgens' was never awaited
    warnings.warn(f"Error cleaning up asyncio loop: {e}", RuntimeWarning)
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_api.py: 1 warning
tests/test_documenso_dashboard.py: 2 warnings
tests/test_documenso_webhook.py: 1 warning
tests/test_documents.py: 1 warning
tests/test_export.py: 1 warning
tests/test_logging.py: 2 warnings
tests/test_login.py: 1 warning
tests/test_numbering.py: 2 warnings
tests/test_reporting.py: 2 warnings
tests/test_search.py: 5 warnings
tests/test_signature.py: 1 warning
tests/test_task17.py: 1 warning
tests/test_task46.py: 1 warning
tests/test_task66.py: 2 warnings
tests/test_token.py: 1 warning
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\messages.py:119: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

tests/test_archive_storage.py::test_archive_writes_files
tests/test_task17.py::test_archival_workflow
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\archive.py:47: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    timestamp=datetime.utcnow(),

tests/test_docker_compose.py::test_docker_compose_services
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\yaml\scanner.py:286: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001BF8EEC0130>
    for level in list(self.possible_simple_keys):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_docker_compose.py::test_docker_compose_services
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\yaml\scanner.py:286: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001BF8EEC2110>
    for level in list(self.possible_simple_keys):
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_hr_sync.py::test_sync_temp_reassignments
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_hr_sync.py:10: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expiry = datetime.utcnow() + timedelta(days=1)

tests/test_hr_sync.py::test_sync_temp_reassignments
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\hr_sync.py:31: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if until <= datetime.utcnow():

tests/test_hr_sync.py::test_sync_temp_reassignments
tests/test_task13.py::test_priority_and_temp_assignment
tests/test_task13.py::test_priority_and_temp_assignment
tests/test_task74.py::test_manager_approval_required
tests/test_task74.py::test_manager_approval_required
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:158: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if (until - datetime.utcnow()).days > TEMP_ASSIGN_MAX_DAYS and not approved:

tests/test_logging.py::test_logging_records_actions
tests/test_numbering.py::test_project_document_numbering
tests/test_reporting.py::test_reporting_endpoints
tests/test_reporting.py::test_reporting_endpoints
tests/test_task13.py::test_priority_and_temp_assignment
tests/test_task13.py::test_priority_and_temp_assignment
tests/test_task13.py::test_priority_and_temp_assignment
tests/test_task88.py::test_execute_query_projects
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:167: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if project.temp_user and project.temp_until and datetime.utcnow() >= project.temp_until:

tests/test_login.py::test_login_flow
tests/test_login.py::test_login_flow
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\starlette\templating.py:162: DeprecationWarning: The `name` is not the first parameter anymore. The first parameter should be the `Request` instance.
  Replace `TemplateResponse(name, {"request": request})` by `TemplateResponse(request, name)`.
    warnings.warn(

tests/test_models.py::test_models_crud
  C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\weakref.py:428: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001BF8D8966B0>
    self.data[ref(key, self._remove)] = value
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_records_keeper.py::test_create_archival_folder
tests/test_task58.py::test_task58_returns_none
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\records_keeper.py:18: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    date_part = datetime.utcnow().strftime("%Y%m%d")

tests/test_sign_approval.py::test_sign_approval_flow
  C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\events.py:835: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001BF8D8944F0>
    def new_event_loop():
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

tests/test_task07.py::test_oidc_token_flow
tests/test_token.py::test_oidc_flow
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\auth.py:133: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

tests/test_task13.py::test_priority_and_temp_assignment
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task13.py:15: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    past = datetime.utcnow() - timedelta(days=1)

tests/test_task13.py::test_priority_and_temp_assignment
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task13.py:21: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    future = datetime.utcnow() + timedelta(hours=1)

tests/test_task13.py::test_priority_and_temp_assignment
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task13.py:26: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    project.temp_until = datetime.utcnow() - timedelta(seconds=1)

tests/test_task46.py::test_admin_access_control
tests/test_task46.py::test_require_role_dependency
tests/test_token.py::test_jwt_token_flow
tests/test_token_env.py::test_env_secret_key
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\auth.py:80: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))

tests/test_task59.py::test_should_purge
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task59.py:15: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    old = datetime.utcnow() - timedelta(days=10)

tests/test_task59.py::test_should_purge
tests/test_task59.py::test_should_purge
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\security_compliance.py:24: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.utcnow() - created > timedelta(days=retention_days)

tests/test_task59.py::test_should_purge
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task59.py:17: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    assert not should_purge(datetime.utcnow(), 5)

tests/test_task59.py::test_should_purge_validation
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task59.py:22: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    should_purge(datetime.utcnow(), 0)

tests/test_task73.py::test_overdue_high_priority_detection
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task73.py:12: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created=datetime.utcnow() - timedelta(days=20),

tests/test_task73.py::test_overdue_high_priority_detection
tests/test_task73.py::test_overdue_high_priority_detection
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:187: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if proj.priority >= 5 and proj.created < datetime.utcnow() - timedelta(days=14):

tests/test_task74.py::test_manager_approval_required
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\test_task74.py:10: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    long_until = datetime.utcnow() + timedelta(days=40)

tests/test_tiptap.py::test_import_tiptap_document
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\tiptap.py:51: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    date=datetime.utcnow(),

tests/test_workflows.py::test_workflow_lifecycle
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\_pytest\threadexception.py:58: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-1 (run)

  Traceback (most recent call last):
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1043, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 994, in run
      self._target(*self._args, **self._kwargs)
      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 67, in run
      return asyncio.run(self.serve(sockets=sockets))
             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
      return runner.run(main)
             ~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
      return self._loop.run_until_complete(task)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 725, in run_until_complete
      return future.result()
             ~~~~~~~~~~~~~^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
      await self._serve(sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 90, in _serve
      await self.shutdown(sockets=sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 275, in shutdown
      await asyncio.sleep(0.1)
  TypeError: object NoneType can't be used in 'await' expression

  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.13.4-final-0 _______________

Name                                         Stmts   Miss Branch BrPart  Cover
------------------------------------------------------------------------------
src\docreview360\__init__.py                     4      0      0      0   100%
src\docreview360\accessibility.py               16      0      8      2    92%
src\docreview360\ai_assist.py                   25      5      8      3    76%
src\docreview360\ai_balancer.py                 25      5     10      5    71%
src\docreview360\ai_utils.py                    55      9     16      0    79%
src\docreview360\api.py                        485     81     48     15    80%
src\docreview360\approvals.py                   35      1      6      3    90%
src\docreview360\archive.py                     37      0      0      0   100%
src\docreview360\auth.py                        81      9     20      7    84%
src\docreview360\autosuggest.py                 18     10      2      0    40%
src\docreview360\backup_panel.py                17      2      0      0    88%
src\docreview360\backup_utils.py                26      1      6      1    94%
src\docreview360\cache.py                       29      3      8      4    81%
src\docreview360\celery_app.py                  68      8     22      6    82%
src\docreview360\cli.py                         33      3      6      1    90%
src\docreview360\codex_editor.py                 8      1      2      1    80%
src\docreview360\comments.py                    30      1      2      1    94%
src\docreview360\compliance_panel.py            13      3      2      0    67%
src\docreview360\config.py                      32      3      4      1    89%
src\docreview360\contextual_help.py             22      2      6      3    82%
src\docreview360\conversion.py                   9      0      0      0   100%
src\docreview360\database.py                    45      3     12      3    89%
src\docreview360\deploy.py                       7      2      0      0    71%
src\docreview360\doc_types.py                   72     11     14      3    84%
src\docreview360\documenso.py                   80      8     30      6    87%
src\docreview360\documents.py                  104     18     24      9    77%
src\docreview360\editor_loader.py               10      1      4      1    86%
src\docreview360\editor_switcher.py             17      1      6      1    91%
src\docreview360\environment.py                 22      0      4      0   100%
src\docreview360\exporter.py                    51      1     14      2    95%
src\docreview360\fann_corpus.py                 24      0      8      0   100%
src\docreview360\fann_model.py                  31      0      6      0   100%
src\docreview360\feature_flags.py               18      0      4      0   100%
src\docreview360\fed_numbering.py               15      0      6      1    95%
src\docreview360\flower.py                      16      1      6      1    91%
src\docreview360\fts.py                         20      1      6      1    92%
src\docreview360\grammar_plugin.py              11      0      4      0   100%
src\docreview360\graphql_api.py                 26      1      2      1    93%
src\docreview360\hr_sync.py                     18      3      4      1    82%
src\docreview360\iac_templates\__init__.py       7      0      2      0   100%
src\docreview360\logs.py                        50      1     12      2    95%
src\docreview360\messages.py                     9      0      0      0   100%
src\docreview360\metabase.py                    45      4      8      3    87%
src\docreview360\metabase_sync.py               11      1      4      1    87%
src\docreview360\metadata.py                     4      0      0      0   100%
src\docreview360\models.py                      56      0      0      0   100%
src\docreview360\monitoring.py                  30      3     10      3    85%
src\docreview360\nemo_guardrails.py              5      0      0      0   100%
src\docreview360\notifications.py               32      0     10      1    98%
src\docreview360\object_storage.py              14      1      4      1    89%
src\docreview360\onlyoffice_editor.py            3      0      0      0   100%
src\docreview360\pandiff.py                     28      1     16      1    95%
src\docreview360\perf.py                        12      1      4      1    88%
src\docreview360\plugin_marketplace.py           9      0      2      0   100%
src\docreview360\plugins.py                     47      4     14      2    90%
src\docreview360\plugins_ui.py                   8      0      2      0   100%
src\docreview360\project_init.py                14      0      4      0   100%
src\docreview360\pyo3_builder.py                 7      0      0      0   100%
src\docreview360\rbac.py                        18      1      2      0    95%
src\docreview360\rbac_editor.py                 15      0      2      0   100%
src\docreview360\records_keeper.py              11      1      2      1    85%
src\docreview360\regression.py                   9      1      2      1    82%
src\docreview360\reporting.py                   37      0      2      0   100%
src\docreview360\schedule_editor.py             14      0      2      0   100%
src\docreview360\search.py                     165     11     54      9    91%
src\docreview360\security_compliance.py         17      1      6      1    91%
src\docreview360\security_hardening.py          28      0      2      0   100%
src\docreview360\security_utils.py               8      0      0      0   100%
src\docreview360\seeds.py                        8      0      0      0   100%
src\docreview360\settings_manager.py            18      0      2      0   100%
src\docreview360\setup_wizard.py                10      0      0      0   100%
src\docreview360\status.py                      12      0      0      0   100%
src\docreview360\template_manager.py            17      1      4      1    90%
src\docreview360\tiptap.py                      31      1      8      2    92%
src\docreview360\tiptap_plugins.py              15      0      4      0   100%
src\docreview360\toast_editor.py                 8      1      2      1    80%
src\docreview360\vector_search.py               70      3     20      1    96%
src\docreview360\wasm_plugin.py                  6      0      0      0   100%
src\docreview360\workflow_components.py         32      2      0      0    94%
src\docreview360\workflow_designer.py           13      1      2      1    87%
src\docreview360\workflows.py                   41      3      8      2    90%
src\docreview360\xml_editor.py                   8      1      2      1    80%
------------------------------------------------------------------------------
TOTAL                                         2657    242    548    119    88%
Required test coverage of 70% reached. Total coverage: 88.05%
================================= Hypothesis ==================================
`git apply .hypothesis\patches\2025-07-13--df91a69c.patch` to add failing examples to your code.
=========================== short test summary info ===========================
FAILED tests/property/test_task63_property.py::test_cache_roundtrip - hypothe...
FAILED tests/test_ai_assist.py::test_ai_rewrite_endpoint - RuntimeError: This...
FAILED tests/test_ai_assist.py::test_ai_summarize_endpoint - RuntimeError: Th...
FAILED tests/test_ai_assist.py::test_call_openai_fallback - RuntimeError: Thi...
FAILED tests/test_ai_assist.py::test_rewrite_validation - RuntimeError: This ...
FAILED tests/test_ai_assist.py::test_summarize_validation - RuntimeError: Thi...
FAILED tests/test_ai_assist.py::test_call_openai_remote - RuntimeError: This ...
FAILED tests/test_ai_assist.py::test_call_openai_error - RuntimeError: This e...
FAILED tests/test_flower.py::test_launch_flower_success - RuntimeError: This ...
FAILED tests/test_flower.py::test_launch_flower_failure - RuntimeError: This ...
FAILED tests/test_flower.py::test_launch_flower_bad_port - RuntimeError: This...
FAILED tests/test_frontend_quality.py::test_pages_have_default_export - Unico...
FAILED tests/test_frontend_quality.py::test_tsx_files_formatted - FileNotFoun...
FAILED tests/test_task135.py::test_task135_completed - RuntimeError: This eve...
FAILED tests/test_task136.py::test_task136_completed - RuntimeError: This eve...
FAILED tests/test_task137.py::test_task137_completed - RuntimeError: This eve...
ERROR tests/e2e/test_approvals_e2e.py::test_approval_lifecycle[chromium] - pl...
ERROR tests/e2e/test_cli_config_e2e.py::test_cli_init_and_config[chromium] - ...
ERROR tests/e2e/test_cli_seed_e2e.py::test_cli_seed_creates_sample[chromium]
ERROR tests/e2e/test_login_e2e.py::test_login_flow[chromium] - playwright._im...
ERROR tests/e2e/test_workflow_e2e.py::test_workflow_end_to_end[chromium] - pl...
16 failed, 359 passed, 2 skipped, 971 warnings, 5 errors in 22.15s

pytest-property..........................................................Failed
- hook id: pytest-property
- exit code: 5

============================== warnings summary ===============================
src\docreview360\search.py:23
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:23: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

src\docreview360\search.py:35
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:35: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

src\docreview360\comments.py:22
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\comments.py:22: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

tests\e2e\test_approvals_e2e.py:26
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_approvals_e2e.py:26: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_cli_config_e2e.py:61
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_cli_config_e2e.py:61: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_cli_seed_e2e.py:65
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_cli_seed_e2e.py:65: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_login_e2e.py:26
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_login_e2e.py:26: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_workflow_e2e.py:25
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_workflow_e2e.py:25: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

<frozen importlib._bootstrap>:530
  <frozen importlib._bootstrap>:530: DeprecationWarning: the load_module() method is deprecated and slated for removal in Python 3.15; use exec_module() instead

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 skipped, 381 deselected, 9 warnings in 1.16s

pytest-e2e...............................................................Failed
- hook id: pytest-e2e
- exit code: 1

EEEEE                                                                    [100%]
=================================== ERRORS ====================================
_____________ ERROR at setup of test_approval_lifecycle[chromium] _____________

launch_browser = <function launch_browser.<locals>.launch at 0x000002C3E973EAC0>

    @pytest.fixture(scope="session")
    def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
>       browser = launch_browser()
                  ^^^^^^^^^^^^^^^^

..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:282:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:274: in launch
    browser = browser_type.launch(**launch_options)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\.venv\Lib\site-packages\playwright\sync_api\_generated.py:14475: in launch
    self._sync(
..\.venv\Lib\site-packages\playwright\_impl\_browser_type.py:98: in launch
    await self._channel.send(
..\.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x000002C3E96AFB60>
cb = <function Channel.send.<locals>.<lambda> at 0x000002C3E973CB80>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:\Users\ericp\AppData\Local\ms-playwright\chromium_headless_shell-1179\chrome-win\headless_shell.exe
E           \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
E           \u2551 Looks like Playwright was just installed or updated.       \u2551
E           \u2551 Please run the following command to download new browsers: \u2551
E           \u2551                                                            \u2551
E           \u2551     playwright install                                     \u2551
E           \u2551                                                            \u2551
E           \u2551 <3 Playwright Team                                         \u2551
E           \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d

..\.venv\Lib\site-packages\playwright\_impl\_connection.py:558: Error
____________ ERROR at setup of test_cli_init_and_config[chromium] _____________

launch_browser = <function launch_browser.<locals>.launch at 0x000002C3E973EAC0>

    @pytest.fixture(scope="session")
    def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
>       browser = launch_browser()
                  ^^^^^^^^^^^^^^^^

..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:282:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:274: in launch
    browser = browser_type.launch(**launch_options)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\.venv\Lib\site-packages\playwright\sync_api\_generated.py:14475: in launch
    self._sync(
..\.venv\Lib\site-packages\playwright\_impl\_browser_type.py:98: in launch
    await self._channel.send(
..\.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x000002C3E96AFB60>
cb = <function Channel.send.<locals>.<lambda> at 0x000002C3E973CB80>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:\Users\ericp\AppData\Local\ms-playwright\chromium_headless_shell-1179\chrome-win\headless_shell.exe
E           \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
E           \u2551 Looks like Playwright was just installed or updated.       \u2551
E           \u2551 Please run the following command to download new browsers: \u2551
E           \u2551                                                            \u2551
E           \u2551     playwright install                                     \u2551
E           \u2551                                                            \u2551
E           \u2551 <3 Playwright Team                                         \u2551
E           \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d

..\.venv\Lib\site-packages\playwright\_impl\_connection.py:558: Error
---------------------------- Captured stderr setup ----------------------------
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted
__________ ERROR at setup of test_cli_seed_creates_sample[chromium] ___________

launch_browser = <function launch_browser.<locals>.launch at 0x000002C3E973EAC0>

    @pytest.fixture(scope="session")
    def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
>       browser = launch_browser()
                  ^^^^^^^^^^^^^^^^

..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:282:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:274: in launch
    browser = browser_type.launch(**launch_options)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\.venv\Lib\site-packages\playwright\sync_api\_generated.py:14475: in launch
    self._sync(
..\.venv\Lib\site-packages\playwright\_impl\_browser_type.py:98: in launch
    await self._channel.send(
..\.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x000002C3E96AFB60>
cb = <function Channel.send.<locals>.<lambda> at 0x000002C3E973CB80>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:\Users\ericp\AppData\Local\ms-playwright\chromium_headless_shell-1179\chrome-win\headless_shell.exe
E           \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
E           \u2551 Looks like Playwright was just installed or updated.       \u2551
E           \u2551 Please run the following command to download new browsers: \u2551
E           \u2551                                                            \u2551
E           \u2551     playwright install                                     \u2551
E           \u2551                                                            \u2551
E           \u2551 <3 Playwright Team                                         \u2551
E           \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d

..\.venv\Lib\site-packages\playwright\_impl\_connection.py:558: Error
---------------------------- Captured stderr setup ----------------------------
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted
_________________ ERROR at setup of test_login_flow[chromium] _________________

launch_browser = <function launch_browser.<locals>.launch at 0x000002C3E973EAC0>

    @pytest.fixture(scope="session")
    def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
>       browser = launch_browser()
                  ^^^^^^^^^^^^^^^^

..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:282:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:274: in launch
    browser = browser_type.launch(**launch_options)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\.venv\Lib\site-packages\playwright\sync_api\_generated.py:14475: in launch
    self._sync(
..\.venv\Lib\site-packages\playwright\_impl\_browser_type.py:98: in launch
    await self._channel.send(
..\.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x000002C3E96AFB60>
cb = <function Channel.send.<locals>.<lambda> at 0x000002C3E973CB80>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:\Users\ericp\AppData\Local\ms-playwright\chromium_headless_shell-1179\chrome-win\headless_shell.exe
E           \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
E           \u2551 Looks like Playwright was just installed or updated.       \u2551
E           \u2551 Please run the following command to download new browsers: \u2551
E           \u2551                                                            \u2551
E           \u2551     playwright install                                     \u2551
E           \u2551                                                            \u2551
E           \u2551 <3 Playwright Team                                         \u2551
E           \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d

..\.venv\Lib\site-packages\playwright\_impl\_connection.py:558: Error
---------------------------- Captured stderr setup ----------------------------
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted
____________ ERROR at setup of test_workflow_end_to_end[chromium] _____________

launch_browser = <function launch_browser.<locals>.launch at 0x000002C3E973EAC0>

    @pytest.fixture(scope="session")
    def browser(launch_browser: Callable[[], Browser]) -> Generator[Browser, None, None]:
>       browser = launch_browser()
                  ^^^^^^^^^^^^^^^^

..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:282:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
..\.venv\Lib\site-packages\pytest_playwright\pytest_playwright.py:274: in launch
    browser = browser_type.launch(**launch_options)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\.venv\Lib\site-packages\playwright\sync_api\_generated.py:14475: in launch
    self._sync(
..\.venv\Lib\site-packages\playwright\_impl\_browser_type.py:98: in launch
    await self._channel.send(
..\.venv\Lib\site-packages\playwright\_impl\_connection.py:69: in send
    return await self._connection.wrap_api_call(
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <playwright._impl._connection.Connection object at 0x000002C3E96AFB60>
cb = <function Channel.send.<locals>.<lambda> at 0x000002C3E973CB80>
is_internal = False, title = None

    async def wrap_api_call(
        self, cb: Callable[[], Any], is_internal: bool = False, title: str = None
    ) -> Any:
        if self._api_zone.get():
            return await cb()
        task = asyncio.current_task(self._loop)
        st: List[inspect.FrameInfo] = getattr(
            task, "__pw_stack__", None
        ) or inspect.stack(0)

        parsed_st = _extract_stack_trace_information_from_stack(st, is_internal, title)
        self._api_zone.set(parsed_st)
        try:
            return await cb()
        except Exception as error:
>           raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
E           playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at C:\Users\ericp\AppData\Local\ms-playwright\chromium_headless_shell-1179\chrome-win\headless_shell.exe
E           \u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
E           \u2551 Looks like Playwright was just installed or updated.       \u2551
E           \u2551 Please run the following command to download new browsers: \u2551
E           \u2551                                                            \u2551
E           \u2551     playwright install                                     \u2551
E           \u2551                                                            \u2551
E           \u2551 <3 Playwright Team                                         \u2551
E           \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d

..\.venv\Lib\site-packages\playwright\_impl\_connection.py:558: Error
---------------------------- Captured stderr setup ----------------------------
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted
============================== warnings summary ===============================
src\docreview360\search.py:23
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:23: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

src\docreview360\search.py:35
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\search.py:35: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

src\docreview360\comments.py:22
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\src\docreview360\comments.py:22: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    created: datetime = datetime.utcnow()

tests\e2e\test_approvals_e2e.py:26
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_approvals_e2e.py:26: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_cli_config_e2e.py:61
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_cli_config_e2e.py:61: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_cli_seed_e2e.py:65
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_cli_seed_e2e.py:65: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_login_e2e.py:26
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_login_e2e.py:26: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

tests\e2e\test_workflow_e2e.py:25
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\DocReview360\tests\e2e\test_workflow_e2e.py:25: PytestUnknownMarkWarning: Unknown pytest.mark.e2e - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.e2e

<frozen importlib._bootstrap>:530
  <frozen importlib._bootstrap>:530: DeprecationWarning: the load_module() method is deprecated and slated for removal in Python 3.15; use exec_module() instead

tests/e2e/test_cli_config_e2e.py::test_cli_init_and_config[chromium]
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\_pytest\threadexception.py:58: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-2 (run)

  Traceback (most recent call last):
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 164, in startup
      server = await loop.create_server(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
      ...<5 lines>...
      )
      ^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 1622, in create_server
      raise OSError(err.errno, msg) from None
  OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted

  During handling of the above exception, another exception occurred:

  Traceback (most recent call last):
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1043, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 994, in run
      self._target(*self._args, **self._kwargs)
      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 67, in run
      return asyncio.run(self.serve(sockets=sockets))
             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
      return runner.run(main)
             ~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
      return self._loop.run_until_complete(task)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 712, in run_until_complete
      self.run_forever()
      ~~~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 683, in run_forever
      self._run_once()
      ~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 2042, in _run_once
      handle._run()
      ~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\events.py", line 89, in _run
      self._context.run(self._callback, *self._args)
      ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
      await self._serve(sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 86, in _serve
      await self.startup(sockets=sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 174, in startup
      sys.exit(1)
      ~~~~~~~~^^^
  SystemExit: 1

  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/e2e/test_cli_seed_e2e.py::test_cli_seed_creates_sample[chromium]
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\_pytest\threadexception.py:58: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-3 (run)

  Traceback (most recent call last):
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 164, in startup
      server = await loop.create_server(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
      ...<5 lines>...
      )
      ^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 1622, in create_server
      raise OSError(err.errno, msg) from None
  OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted

  During handling of the above exception, another exception occurred:

  Traceback (most recent call last):
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1043, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 994, in run
      self._target(*self._args, **self._kwargs)
      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 67, in run
      return asyncio.run(self.serve(sockets=sockets))
             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
      return runner.run(main)
             ~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
      return self._loop.run_until_complete(task)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 712, in run_until_complete
      self.run_forever()
      ~~~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 683, in run_forever
      self._run_once()
      ~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 2042, in _run_once
      handle._run()
      ~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\events.py", line 89, in _run
      self._context.run(self._callback, *self._args)
      ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
      await self._serve(sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 86, in _serve
      await self.startup(sockets=sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 174, in startup
      sys.exit(1)
      ~~~~~~~~^^^
  SystemExit: 1

  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/e2e/test_login_e2e.py::test_login_flow[chromium]
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\_pytest\threadexception.py:58: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-4 (run)

  Traceback (most recent call last):
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 164, in startup
      server = await loop.create_server(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
      ...<5 lines>...
      )
      ^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 1622, in create_server
      raise OSError(err.errno, msg) from None
  OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted

  During handling of the above exception, another exception occurred:

  Traceback (most recent call last):
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1043, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 994, in run
      self._target(*self._args, **self._kwargs)
      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 67, in run
      return asyncio.run(self.serve(sockets=sockets))
             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
      return runner.run(main)
             ~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
      return self._loop.run_until_complete(task)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 712, in run_until_complete
      self.run_forever()
      ~~~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 683, in run_forever
      self._run_once()
      ~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 2042, in _run_once
      handle._run()
      ~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\events.py", line 89, in _run
      self._context.run(self._callback, *self._args)
      ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
      await self._serve(sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 86, in _serve
      await self.startup(sockets=sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 174, in startup
      sys.exit(1)
      ~~~~~~~~^^^
  SystemExit: 1

  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

tests/e2e/test_workflow_e2e.py::test_workflow_end_to_end[chromium]
  C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\_pytest\threadexception.py:58: PytestUnhandledThreadExceptionWarning: Exception in thread Thread-5 (run)

  Traceback (most recent call last):
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 164, in startup
      server = await loop.create_server(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
      ...<5 lines>...
      )
      ^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 1622, in create_server
      raise OSError(err.errno, msg) from None
  OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000): [winerror 10048] only one usage of each socket address (protocol/network address/port) is normally permitted

  During handling of the above exception, another exception occurred:

  Traceback (most recent call last):
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1043, in _bootstrap_inner
      self.run()
      ~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 994, in run
      self._target(*self._args, **self._kwargs)
      ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 67, in run
      return asyncio.run(self.serve(sockets=sockets))
             ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 195, in run
      return runner.run(main)
             ~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\runners.py", line 118, in run
      return self._loop.run_until_complete(task)
             ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 712, in run_until_complete
      self.run_forever()
      ~~~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 683, in run_forever
      self._run_once()
      ~~~~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\base_events.py", line 2042, in _run_once
      handle._run()
      ~~~~~~~~~~~^^
    File "C:\Users\ericp\AppData\Local\Programs\Python\Python313\Lib\asyncio\events.py", line 89, in _run
      self._context.run(self._callback, *self._args)
      ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
      await self._serve(sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 86, in _serve
      await self.startup(sockets=sockets)
    File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\uvicorn\server.py", line 174, in startup
      sys.exit(1)
      ~~~~~~~~^^^
  SystemExit: 1

  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.
    warnings.warn(pytest.PytestUnhandledThreadExceptionWarning(msg))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/e2e/test_approvals_e2e.py::test_approval_lifecycle[chromium] - pl...
ERROR tests/e2e/test_cli_config_e2e.py::test_cli_init_and_config[chromium] - ...
ERROR tests/e2e/test_cli_seed_e2e.py::test_cli_seed_creates_sample[chromium]
ERROR tests/e2e/test_login_e2e.py::test_login_flow[chromium] - playwright._im...
ERROR tests/e2e/test_workflow_e2e.py::test_workflow_end_to_end[chromium] - pl...
1 skipped, 376 deselected, 13 warnings, 5 errors in 6.99s

mutmut...................................................................Failed
- hook id: mutmut
- exit code: 1

Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Scripts\mutmut.EXE\__main__.py", line 4, in <module>
    from mutmut.__main__ import cli
  File "C:\Users\ericp\Documents\Vengeance Coding and Script Files\DocReview360\.venv\Lib\site-packages\mutmut\__main__.py", line 9, in <module>
    import resource
ModuleNotFoundError: No module named 'resource'
## Dev Gate Results - 2025-07-15T20:13:15Z
- **mypy**: failed – `src/docreview360/cache.py:27: error: Item "bool" of "Any | bool" has no attribute "ping"`
- **bandit**: passed – 0 high severity issues
- **semgrep**: failed – blocked from downloading `p/ci` ruleset
- **pytest**: passed – 397 tests passed (90% coverage)
- **pytest (property)**: passed – 1 skipped, 399 deselected
- **pytest (e2e)**: passed – 1 skipped, 399 deselected
- **mutmut**: aborted – run interrupted
