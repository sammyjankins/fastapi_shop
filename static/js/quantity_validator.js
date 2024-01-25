function validateQuantity(inputElement) {
    var inputValue = inputElement.value;

    if (isNaN(inputValue)) {
        appendAlert("Please enter a valid number.");
        inputElement.value = "";
    }

    if (inputValue < 1) {
        appendAlert("Please enter a number from 1");
        inputElement.value = "";
    }
}