var clickBool = false;

$('body').on('click', function(e) {
    var target, href;
    target = $(e.target);
    if (e.target.tagName === 'A' && e.target.id !== '') {
        clickBool = true;
        e.preventDefault();

        if (window.confirm("Are you sure you want to leave? You will lose progress on the current form.")) {
            if (e.target.tagName === 'A') {
                href = target.attr('href');
            } else {
                href = target.parents('a').first().attr('href');
            }
            window.location.href = href;
        }
    }
});

window.onbeforeunload = function() {
    if (!clickBool) {
        return true;
    }
};