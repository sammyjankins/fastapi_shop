const checkboxes = document.querySelectorAll('input.childCheckbox[type="checkbox"]');
const submitButton = document.querySelector('.submit-button');
const copyLinks = document.querySelectorAll('.id-copy-link');

checkboxes.forEach(function (checkbox) {
    checkbox.addEventListener('change', function () {
        const atLeastOneChecked = Array.from(checkboxes).some(cb => cb.checked);
        if (atLeastOneChecked) {
            submitButton.removeAttribute('disabled');
        } else {
            submitButton.setAttribute('disabled', 'disabled');
        }
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const masterCheckbox = document.getElementById('masterCheckbox');
    const childCheckboxes = document.querySelectorAll('.childCheckbox');

    masterCheckbox.addEventListener('change', function () {
        childCheckboxes.forEach(function (checkbox) {
            checkbox.checked = masterCheckbox.checked;
        });
        if (checkboxes.length > 0) {
            if (masterCheckbox.checked) {
                submitButton.removeAttribute('disabled');
            } else {
                submitButton.setAttribute('disabled', 'disabled');
            }
        }
    });

    childCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            const allChecked = Array.from(childCheckboxes).every(cb => cb.checked);
            masterCheckbox.checked = allChecked;
        });
    });
});

copyLinks.forEach(function (link) {
    link.addEventListener('click', function (event) {
        const orderId = event.currentTarget.id;

        const tempInput = document.createElement('input');
        tempInput.hidden = true;
        tempInput.value = orderId;
        document.body.appendChild(tempInput);

        tempInput.select();
        navigator.clipboard.writeText(orderId).then(function () {
            console.log('Text copied to clipboard');

            const snackbar = document.getElementById("snackbar");
            snackbar.style.visibility = "visible";

            setTimeout(function () {
                snackbar.style.visibility = "hidden";
            }, 2000);

        }).catch(function (err) {
            console.error('Failed to copy text', err);
        }).finally(function () {
            document.body.removeChild(tempInput);
        });

        event.preventDefault();
    });
});

