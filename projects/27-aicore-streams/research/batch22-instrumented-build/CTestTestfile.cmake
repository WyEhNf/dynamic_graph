# CMake generated Testfile for 
# Source directory: F:/Hackathon/projects/27-aicore-streams
# Build directory: F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test([=[scheduler_semantics]=] "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/simulator_tests.exe")
set_tests_properties([=[scheduler_semantics]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;30;add_test;F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;0;")
add_test([=[submission_model_and_json]=] "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/model_tests.exe")
set_tests_properties([=[submission_model_and_json]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;33;add_test;F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;0;")
add_test([=[assignment_grouping_equivalence]=] "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/assignment_tests.exe")
set_tests_properties([=[assignment_grouping_equivalence]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;36;add_test;F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;0;")
add_test([=[local_batch_quick]=] "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/aicore_bench.exe" "--input" "F:/Hackathon/projects/27-aicore-streams/data/quick.json" "--output" "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/test-reports/quick-results.json" "--failures" "F:/Hackathon/projects/27-aicore-streams/research/batch22-instrumented-build/test-reports/quick-failures.json")
set_tests_properties([=[local_batch_quick]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;39;add_test;F:/Hackathon/projects/27-aicore-streams/CMakeLists.txt;0;")
