function logAdminAction(action, detail) {
    const logs = document.getElementById('admin-logs');
    const time = new Date().toLocaleTimeString();
    logs.innerHTML += `<div>[${time}] <strong>${action.toUpperCase()}</strong>: ${JSON.stringify(detail)}</div>`;
    logs.scrollTop = logs.scrollHeight;
}

async function adminAction(actionType) {
    const id = document.getElementById('book-id').value.trim();
    const title = document.getElementById('book-title').value.trim();
    const metadata = document.getElementById('book-metadata').value.trim();
    const summary = document.getElementById('book-summary').value.trim();

    try {
        let result;
        if (actionType === 'add') {
            const data = { title, metadata, summary };
            result = await API.addBook(data);
            logAdminAction('Added Book', result);
        } 
        else if (actionType === 'update') {
            if (!id) return alert("ID Buku harus diisi untuk update.");
            const data = { title, metadata, summary };
            result = await API.updateBook(id, data);
            logAdminAction('Updated Book', result);
        } 
        else if (actionType === 'delete') {
            if (!id) return alert("ID Buku harus diisi untuk delete.");
            result = await API.deleteBook(id);
            logAdminAction('Deleted Book', result);
        }

        // Segarkan status database setiap ada perubahan
        await fetchDatabaseStatus();

    } catch (error) {
        logAdminAction('Error', error.message);
    }
}

async function fetchDatabaseStatus() {
    try {
        const result = await API.getDatabaseStatus();
        logAdminAction('DB_STATUS', result);
    } catch (error) {
        logAdminAction('Error Fetching Status', error.message);
    }
}

// Fetch status as soon as admin page loads initially
document.addEventListener('DOMContentLoaded', () => {
    fetchDatabaseStatus();
});