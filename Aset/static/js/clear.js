// clear.js - Menghapus semua jejak (logs, session, cookies, dll)

$(document).ready(function() {
    console.log('Clear.js loaded');
    
    // ===== FUNGSI WAKTU =====
    function getTime() {
        var d = new Date();
        return String(d.getHours()).padStart(2,'0') + ':' + 
               String(d.getMinutes()).padStart(2,'0') + ':' + 
               String(d.getSeconds()).padStart(2,'0');
    }
    
    // ===== FUNGSI TAMBAH LOG KE CONSOLE =====
    function addLogToConsole(msg, type) {
        var icons = {
            'error': '✖',
            'success': '✔',
            'warning': '⚠',
            'info': '⏺'
        };
        var icon = icons[type] || '▪';
        var time = getTime();
        
        var entry = `
            <div class="log-entry log-${type}">
                <span class="log-time">${time}</span>
                <span class="log-icon">${icon}</span>
                <span class="log-msg">${msg}</span>
            </div>
        `;
        $('#console-content').append(entry);
        
        // Update log count
        var count = $('#console-content .log-entry').length;
        $('#log-count').text(count + ' logs');
        
        // Scroll ke bawah
        var el = document.getElementById('console-body');
        if (el) el.scrollTop = el.scrollHeight;
    }
    
    // ===== FUNGSI CLEAR LOGS SAJA (HAPUS LOG DI CONSOLE) =====
    window.clearLogsOnly = function() {
        if ($('#console-content').length > 0) {
            $('#console-content').empty();
            var count = $('#console-content .log-entry').length;
            $('#log-count').text(count + ' logs');
            addLogToConsole('Logs cleared', 'warning');
            return true;
        }
        return false;
    };
    
    // ===== FUNGSI CLEAR SEMUA JEJAK (PANGGIL API) =====
    window.clearAllTraces = function() {
        var $btn = $('#clearTracesBtn');
        
        // Tampilkan loading
        $btn.text('⏳...');
        $btn.css('opacity', '0.5');
        $btn.css('cursor', 'not-allowed');
        
        // Tambah log
        addLogToConsole('Clearing all traces...', 'warning');
        
        // Panggil API clear traces
        $.ajax({
            url: '/clear-and-exit',
            type: 'POST',
            timeout: 5000,
            success: function(response) {
                if (response.status === 200) {
                    // Tambah log sukses
                    addLogToConsole('All traces cleared! Exiting...', 'success');
                    
                    // Ubah tombol
                    $btn.text('✅');
                    $btn.css('color', '#00cc44');
                    $btn.css('border-color', '#00cc44');
                    $btn.css('opacity', '1');
                    $btn.css('cursor', 'default');
                    
                    // Redirect ke logout setelah 1 detik
                    setTimeout(function() {
                        window.location.href = '/logout';
                    }, 1000);
                    
                    // Force close setelah 3 detik
                    setTimeout(function() {
                        window.close();
                        window.location.href = 'about:blank';
                    }, 3000);
                } else {
                    // Gagal
                    addLogToConsole('Failed: ' + (response.message || 'Unknown error'), 'error');
                    
                    $btn.text('❌');
                    $btn.css('color', '#ff2222');
                    $btn.css('opacity', '1');
                    $btn.css('cursor', 'pointer');
                    
                    setTimeout(function() {
                        $btn.text('🗑️ Clear');
                        $btn.css('color', '#ff5555');
                        $btn.css('border-color', '');
                    }, 2000);
                }
            },
            error: function(xhr, status, error) {
                // Error
                addLogToConsole('Clear error: ' + error, 'error');
                
                $btn.text('❌');
                $btn.css('color', '#ff2222');
                $btn.css('opacity', '1');
                $btn.css('cursor', 'pointer');
                
                setTimeout(function() {
                    $btn.text('🗑️ Clear');
                    $btn.css('color', '#ff5555');
                    $btn.css('border-color', '');
                }, 2000);
            }
        });
    };
    
    // ===== TOMBOL CLEAR =====
    $('#clearTracesBtn').off('click').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // Konfirmasi
        if (confirm('⚠️ YAKIN INGIN MENGHAPUS SEMUA JEJAK?\n\nSemua data akan dihapus dan aplikasi akan keluar otomatis!')) {
            window.clearAllTraces();
        }
    });
    
    // ===== TOMBOL CLEAR LOGS SAJA (OPSIONAL) =====
    // Jika ada tombol dengan id #clearLogsBtn
    $('#clearLogsBtn').off('click').on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        if (confirm('Hapus semua log di console?')) {
            window.clearLogsOnly();
        }
    });
    
    console.log('Clear.js ready - Functions available: clearLogsOnly(), clearAllTraces()');
});