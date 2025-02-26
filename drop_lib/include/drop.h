#if !defined(DROP_H)
#define DROP_H

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#define DROP_MAX_FIELD_COUNT 32

struct drop_meta_type_s;
struct drop_meta_field_s;

struct drop_meta_field_s {
    const struct drop_meta_type_s* type;
    const char* name;
    const void* offset;
    const bool initialized;
    const bool is_array;
    const size_t array_count;
};

struct drop_meta_type_s {
    const char* name;
    const struct drop_meta_field_s fields[DROP_MAX_FIELD_COUNT];
    const size_t size;
};

void* drop_meta_read_field(const struct drop_meta_field_s* field, void* object);
const struct drop_meta_field_s* drop_meta_get_field_by_name(const struct drop_meta_type_s* type, const char* name,
                                                            size_t max_name_size);

#define DROP_REFLECT_STRUCT(struct_name) extern const struct drop_meta_type_s struct_name##_meta

#endif  // DROP_H
