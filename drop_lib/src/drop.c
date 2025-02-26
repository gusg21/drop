#include "drop.h"

#include <string.h>

void* drop_meta_read_field(const struct drop_meta_field_s* field, void* object) {
    // Index field->offset bytes into object.
    return (void*)((uintptr_t)object + (uintptr_t)field->offset);
}

const struct drop_meta_field_s* drop_meta_get_field_by_name(const struct drop_meta_type_s* type, const char* name,
                                                            size_t max_name_length) {
    for (uint32_t field_index = 0; field_index < DROP_MAX_FIELD_COUNT; field_index++) {
        const struct drop_meta_field_s* field = &type->fields[field_index];
        if (field->initialized) {
            if (memcmp(field->name, name, max_name_length)) {
                return field;
            }
        } else {
            break;
        }
    }

    return NULL;
}
