const struct drop_meta_type_s {{ struct.name }}_meta = {
    .name = "{{ struct.name }}",
    .fields = {
        {% for field in struct.fields %}
        {
            .name = "{{ field.name }}",
            .type = &{{ field.type }}_meta,
            .offset = (void*)offsetof(struct {{ struct.name }}, {{ field.name }}),
            .initialized = true,
            .is_array = {{ "true" if field.is_array else "false" }},
            .array_count = {{ field.array_count }}
        },
        {% endfor %}
    },
    .size = sizeof(struct {{ struct.name }})
};
