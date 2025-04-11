// Search Functionality (jQuery)
$('#searchInput').on('keyup', function () {
    const searchText = $(this).val().toLowerCase();
    $('#studentTableBody tr').filter(function () {
        const name = $(this).find('td:eq(0)').text().toLowerCase();
        const rollNo = $(this).find('td:eq(1)').text().toLowerCase();
        const department = $(this).find('td:eq(3)').text().toLowerCase();
        $(this).toggle(
            name.includes(searchText) ||
            rollNo.includes(searchText) ||
            department.includes(searchText)
        );
    });
});

// Modal Functionality
document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM fully loaded and parsed");

    // Add Student Modal
    const addStudentBtn = document.getElementById('addStudentBtn');
    const closeAddModal = document.getElementById('closeAddModal');
    const addStudentModal = document.getElementById('addStudentModal');
    const addStudentForm = document.getElementById('addStudentForm');

    // Edit Student Modal
    const editStudentModal = document.getElementById('editStudentModal');
    const closeEditModal = document.getElementById('closeEditModal');
    const editStudentForm = document.getElementById('editStudentForm');

    // Overlay
    const overlay = document.querySelector('.overlay');

    // Show Add Student Modal
    if (addStudentBtn && addStudentModal && overlay) {
        addStudentBtn.addEventListener('click', function () {
            console.log("Add Student button clicked");
            addStudentModal.style.display = 'block';
            overlay.style.display = 'block';
        });
    }

    // Close Add Student Modal
    if (closeAddModal && addStudentModal && overlay) {
        closeAddModal.addEventListener('click', function () {
            console.log("Close Add Student Modal button clicked");
            addStudentModal.style.display = 'none';
            overlay.style.display = 'none';
        });
    }

    // Show Edit Student Modal
    document.querySelectorAll('.editStudentBtn').forEach(button => {
        button.addEventListener('click', function () {
            console.log("Edit Student button clicked");
            const row = this.closest('tr');
            const studentRollno = row.getAttribute('data-rollno');
            const studentName = row.querySelector('td:nth-child(1)').textContent;
            const studentDepartment = row.querySelector('td:nth-child(4)').textContent;
            const studentYearOfStudy = row.querySelector('td:nth-child(5)').textContent;

            document.getElementById('editStudentId').value = studentRollno;
            document.getElementById('editName').value = studentName;
            document.getElementById('editRollno').value = studentRollno;
            document.getElementById('editDepartment').value = studentDepartment;
            document.getElementById('editYearOfStudy').value = studentYearOfStudy;

            editStudentModal.style.display = 'block';
            overlay.style.display = 'block';
        });
    });

    // Close Edit Student Modal
    if (closeEditModal && editStudentModal && overlay) {
        closeEditModal.addEventListener('click', function () {
            console.log("Close Edit Student Modal button clicked");
            editStudentModal.style.display = 'none';
            overlay.style.display = 'none';
        });
    }

    // Add Student Form Submission
    if (addStudentForm) {
        addStudentForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent the default form submission
            console.log("Add Student form submitted");

            const formData = new FormData(this); // Create a FormData object from the form

            fetch('/studdb', {
                method: 'POST',
                body: formData,
            })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    location.reload(); // Reload the page to see the new student
                })
                .catch(error => {
                    alert('Error adding student: ' + error.message);
                });
        });
    }

    // Edit Student Form Submission
    if (editStudentForm) {
        editStudentForm.addEventListener('submit', function (event) {
            event.preventDefault(); // Prevent the default form submission
            console.log("Edit Student form submitted");

            const studentRollno = document.getElementById('editStudentId').value;
            const formData = new FormData(this); // Create a FormData object from the form

            fetch(`/studdb/${studentRollno}`, {
                method: 'PUT',
                body: formData,
            })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    location.reload(); // Reload the page to see the updated student
                })
                .catch(error => {
                    alert('Error updating student: ' + error.message);
                });
        });
    }

    // Delete Student
    document.querySelectorAll('.deleteStudentBtn').forEach(button => {
        button.addEventListener('click', function () {
            console.log("Delete Student button clicked");
            const row = this.closest('tr');
            const studentRollno = row.getAttribute('data-rollno');

            if (confirm('Are you sure you want to delete this student?')) {
                fetch(`/studdb/${studentRollno}`, {
                    method: 'DELETE',
                })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        location.reload(); // Reload the page to see the updated list
                    })
                    .catch(error => {
                        alert('Error deleting student: ' + error.message);
                    });
            }
        });
    });
});

// Lab Request Functionality (jQuery)
$(document).ready(function () {
    // Handle lab request submission
    $('#labRequestForm').on('submit', function (event) {
        event.preventDefault(); // Prevent the default form submission

        $.ajax({
            type: 'POST',
            url: '/studmenu/submit_lab_request',
            data: $(this).serialize(), // Serialize the form data
            success: function (response) {
                // Display success message
                $('#message').text(response.message).css('color', 'green');
            },
            error: function (xhr) {
                // Display error message
                $('#message').text(xhr.responseJSON.message).css('color', 'red');
            }
        });
    });

    // Handle lab request cancellation
    $('#cancelRequestForm').on('submit', function (event) {
        event.preventDefault(); // Prevent the default form submission

        $.ajax({
            type: 'POST',
            url: '/studmenu/cancel_lab_request',
            data: $(this).serialize(), // Serialize the form data
            success: function (response) {
                // Display success message
                $('#message').text(response.message).css('color', 'green');
            },
            error: function (xhr) {
                // Display error message
                $('#message').text(xhr.responseJSON.message).css('color', 'red');
            }
        });
    });
});