idf_component_register(
    SRCS        "feature_extractor.c"
    INCLUDE_DIRS "."
)

target_link_libraries(${COMPONENT_LIB} PRIVATE m)
