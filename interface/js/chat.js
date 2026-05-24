let selectedBookIds = [];

function toggleBookSelection(bookId, title) {
    const index = selectedBookIds.indexOf(bookId);
    if (index > -1) {
        selectedBookIds.splice(index, 1); // remove
    } else {
        selectedBookIds.push(bookId); // add
    }
    updateSelectedBooksUI();
}

function updateSelectedBooksUI() {
    const container = document.getElementById('selected-books-container');
    const list = document.getElementById('selected-books-list');
    
    list.innerHTML = '';
    
    if (selectedBookIds.length > 0) {
        container.style.display = 'block';
        selectedBookIds.forEach(id => {
            const li = document.createElement('li');
            li.textContent = `Buku ID: ${id}`;
            list.appendChild(li);
        });
    } else {
        container.style.display = 'none';
    }
}

function clearSelectedBooks() {
    selectedBookIds = [];
    updateSelectedBooksUI();
    // Uncheck all checkboxes visually
    document.querySelectorAll('.book-checkbox').forEach(cb => cb.checked = false);
}

function appendMessage(sender, text, isHtml = false) {
    const chatBox = document.getElementById('chat-box');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender === 'user' ? 'user-msg' : 'bot-msg'}`;
    
    if (isHtml) {
        msgDiv.innerHTML = `<strong>${sender === 'user' ? 'Kamu' : 'RAG Bot'}:</strong> <br>${text}`;
    } else {
        msgDiv.innerHTML = `<strong>${sender === 'user' ? 'Kamu' : 'RAG Bot'}:</strong> <br>${text}`;
    }
    
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    appendMessage('user', query);
    input.value = '';
    
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;

    try {
        if (selectedBookIds.length > 0) {
            // Mode Deep QA: Tanya konteks spesifik dari buku yang dichecklist
            appendMessage('bot', '<em>Memproses pertanyaan mendalam tentang buku terpilih...</em>', true);
            const res = await API.askDeepQA(query, selectedBookIds);
            
            // Hapus pesan loading (elemen terakhir)
            const chatBox = document.getElementById('chat-box');
            chatBox.removeChild(chatBox.lastChild);
            
            appendMessage('bot', res.answer || "Tidak ada jawaban yang dikembalikan dari API.", false);
        } else {
            // Mode Rekomendasi Biasa
            appendMessage('bot', '<em>Mencari rekomendasi...</em>', true);
            const res = await API.askRecommendation(query);
            
            const chatBox = document.getElementById('chat-box');
            chatBox.removeChild(chatBox.lastChild);
            
            let replyHtml = `<p>${res.answer || "Berikut hasil pencarian dari RAG:"}</p>`;
            
            if (res.recommendations && res.recommendations.length > 0) {
                res.recommendations.forEach(book => {
                    const metadataParts = [
                        book.mata_pelajaran ? `Mata pelajaran: ${book.mata_pelajaran}` : null,
                        book.jenjang ? `Jenjang: ${book.jenjang}` : null,
                        book.kelas ? `Kelas: ${book.kelas}` : null
                    ].filter(Boolean);
                    const metadataText = metadataParts.length > 0 ? metadataParts.join(" | ") : "-";

                    let coverHtml = '';
                    if (book.cover_image) {
                        coverHtml = `<img src="${book.cover_image}" alt="Cover ${book.title}" style="max-width: 100px; max-height: 150px; display: block; margin-top: 10px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px;" onclick="document.querySelector('#checkbox-${book.book_id}').click();" title="Klik untuk pilih dan tanya mendalam">`;
                    }

                    replyHtml += `
                        <div class="book-card" style="display: flex; gap: 15px; align-items: start;">
                            <div style="flex: 1;">
                                <label style="display: block; font-size: 1.1em; cursor: pointer;">
                                    <input type="checkbox" id="checkbox-${book.book_id}" class="book-checkbox" onchange="toggleBookSelection('${book.book_id}', '${book.title.replace(/'/g, "\\'")}')">
                                    <strong>${book.title}</strong>
                                </label>
                                ${coverHtml}
                            </div>
                            <div style="flex: 3;">
                                <p style="margin: 5px 0; font-size: 0.9em; color: #555;">Metadata: ${metadataText}</p>
                                <p style="margin: 5px 0; font-size: 0.9em;"><em>Ringkasan:</em> ${book.summary}</p>
                            </div>
                        </div>
                    `;
                });
            }
            appendMessage('bot', replyHtml, true);
        }
    } catch (error) {
        console.error("Chat error:", error);
        appendMessage('bot', `<span style="color:red">Error menghubungi server: ${error.message}</span>`, true);
    } finally {
        sendBtn.disabled = false;
    }
}