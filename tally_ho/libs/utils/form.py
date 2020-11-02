def lower_case_form_data(self, super_class, key_names):
    """
    Clean form data
    """
    cleaned_data = super(super_class, self).clean()
    if len(key_names) > 1:
        for key in key_names:
            name = cleaned_data.get(key)
            cleaned_data[key] = name.lower()
    else:
        key = key_names[0]
        name = cleaned_data.get(key)
        cleaned_data[key] = name.lower()

    return cleaned_data
