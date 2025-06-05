function toggleList(button) {
    const ul = button.nextElementSibling;
    const isVisible = !ul.classList.contains('d-none');
    ul.classList.toggle('d-none');

    const label = button.dataset.label;
    button.textContent = (isVisible ? '▶ ' : '▼ ') + label;
}


let selectedSourceId = localStorage.getItem('selectedSourceId') || "";
let selectedReceiverId = localStorage.getItem('selectedReceiverId') || "";

document.addEventListener('DOMContentLoaded', () => {
    if (selectedSourceId) {
        const sourceElement = document.querySelector(`.list-group-item[data-id="${selectedSourceId}"]`);
        if (sourceElement) {
            sourceElement.classList.add('active-source');
            document.getElementById('selected-source').innerText = sourceElement.innerText;
        }
    }

    if (selectedReceiverId) {
        const receiverElement = document.querySelector(`.list-group-item[data-id="${selectedReceiverId}"]`);
        if (receiverElement) {
            receiverElement.classList.add('active-receiver');
            document.getElementById('selected-receiver').innerText = receiverElement.innerText;
            fetchCurrentSender(selectedReceiverId);
        }
    }
});

function selectSource(id, element) {
    selectedSourceId = id;
    localStorage.setItem('selectedSourceId', id);
    document.querySelectorAll('.list-group-item').forEach(item => item.classList.remove('active-source'));
    element.classList.add('active-source');
    document.getElementById('selected-source').innerText = element.innerText;
    checkSourceMismatch();
}

function selectReceiver(id, element) {
    selectedReceiverId = id;
    localStorage.setItem('selectedReceiverId', id);
    document.querySelectorAll('.list-group-item').forEach(item => item.classList.remove('active-receiver'));
    element.classList.add('active-receiver');
    document.getElementById('selected-receiver').innerText = element.innerText;
    fetchCurrentSender(id);
}

function fetchCurrentSender(receiverId) {
    fetch(`/get_current_sender/${receiverId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                document.getElementById('current-sender').innerText = `${data.current_sender_node} - ${data.current_sender_label}`;
            } else {
                document.getElementById('current-sender').innerText = 'Unknown';
            }
            checkSourceMismatch();
        })
        .catch(() => {
            document.getElementById('current-sender').innerText = 'Unknown';
            checkSourceMismatch();
        });
}

function checkSourceMismatch() {
    const selectedSourceText = document.getElementById('selected-source').innerText;
    const currentSenderText = document.getElementById('current-sender').innerText;
    const selectedSourceElement = document.getElementById('selected-source');

    const currentIsUnknown = currentSenderText === "Unknown" || currentSenderText.trim() === "";
}

function changeSource() {
    if (!selectedSourceId || !selectedReceiverId) {
        alert('Please select both a source and a destination.');
        return;
    }

    fetch('/change_source', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            receiver_id: selectedReceiverId,
            sender_id: selectedSourceId
        })
    })
    .then(response => response.json())
    .then(data => {
        const msgEl = document.getElementById('success-message');
        if (data.status === 'success') {
            msgEl.innerText = 'Take successful';
            msgEl.style.color = 'green';
            fetchCurrentSender(selectedReceiverId);
        } else {
            msgEl.innerText = `Error: ${data.message}`;
            msgEl.style.color = 'red';
        }
    })
    .catch(() => {
        const msgEl = document.getElementById('success-message');
        msgEl.innerText = 'An error occurred while changing the source.';
        msgEl.style.color = 'red';
    });
}

function disconnectReceiver() {
    fetch('/disconnect_receiver', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ receiver_id: selectedReceiverId })
    })
    .then(response => response.json())
    .then(data => {
        const msgEl = document.getElementById('success-message');
        if (data.status === 'success') {
            msgEl.innerText = 'Disconnected successfully';
            msgEl.style.color = 'green';
            document.getElementById('current-sender').innerText = 'Unknown';
            checkSourceMismatch();
        } else {
            msgEl.innerText = `Error: ${data.message}`;
            msgEl.style.color = 'red';
        }
    })
    .catch(() => {
        const msgEl = document.getElementById('success-message');
        msgEl.innerText = 'An error occurred while disconnecting the receiver.';
        msgEl.style.color = 'red';
    });
}