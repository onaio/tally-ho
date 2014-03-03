function validate_results(blank_message) {
    var required_fields = Array.filter(
        document.getElementsByClassName('required'),
        function(el) {
            return el.nodeName == 'INPUT';
        }
    );

    var valid = true;
    var i = 0;
    for (i = 0; i < required_fields.length; i++) {
        var elem = required_fields[i];
        if (elem.value == ""){
            valid = false;
            elem.parentNode.setAttribute('class', 'has-error');
        } else {
            elem.parentNode.setAttribute('class', 'has-success');
        }
    }
    if (valid === false) {
        alert(blank_message);
    }
    return valid;
}
