let socket;
let parTaskId = localStorage.getItem('parTaskId');

function initializeSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        if (parTaskId) {
            // 연결 시 서버에 현재 진행 중인 PAR 작업이 있음을 알림
            socket.emit('resume_par', { task_id: parTaskId });
        }
    });

    socket.on('par_started', (data) => {
        parTaskId = data.task_id;
        localStorage.setItem('parTaskId', parTaskId);
        showParOverlay();
        updateParButton();
    });

    socket.on('par_status_update', (data) => {
        updateParOverlay(data);
    });

    socket.on('par_input_required', (data) => {
        showInputModal(data.input_data.message, data.input_data.fast_search_results);
    });

    socket.on('par_completed', (data) => {
        updateParOverlay(data);
        localStorage.removeItem('parTaskId');
        parTaskId = null;
        updateParButton();
    });

    socket.on('par_error', (data) => {
        $('#parError').text(`Error: ${data.error}`).show();
        localStorage.removeItem('parTaskId');
        parTaskId = null;
        updateParButton();
    });
}


function startPAR(query) {
    if (parTaskId) {
        alert('A PAR process is already running. Please wait for it to complete.');
        return;
    }
    socket.emit('start_par', { query: query });
}

function sendPARInput(userResponse) {
    socket.emit('par_input', { task_id: parTaskId, response: userResponse });
}

function showInputModal(message, fastSearchResults) {
    $('#parModalMessage').text(message);
    $('#parModalFastSearchResults').html(fastSearchResults);
    $('#parModal').show();
}

function updateParOverlay(data) {
    $('#parStatus').text(data.status);
    $('#parProgress').css('width', `${data.progress}%`).attr('aria-valuenow', data.progress).text(`${data.progress}%`);

    if (data.current_stage) {
        $('#parCurrentStage').text(`Current Stage: ${data.current_stage}`);
    }

    if (data.status === 'completed') {
        $('#viewResults').show();
        $('#parOverlay').addClass('bounce');
        setTimeout(() => $('#parOverlay').removeClass('bounce'), 1000);
    }
}

function updateParButton() {
    const parButton = $('.par-search-btn');
    if (parTaskId) {
        parButton.prop('disabled', true).text('PAR in progress...');
    } else {
        parButton.prop('disabled', false).text('Powerful-Auto-Researcher');
    }
}

function showParOverlay() {
    $('#parOverlay').show();
}

function hideParOverlay() {
    $('#parOverlay').hide();
}




$(document).ready(function() {
    initializeSocket();
    // 기존의 클릭 이벤트 핸들러 제거
    $('.par-search-btn').off('click');

    if (parTaskId) {
        showParOverlay();
        updateParButton();
        // 서버에 현재 상태 요청
        socket.emit('get_par_status', { task_id: parTaskId });
    }

    // 새로운 클릭 이벤트 핸들러 등록
    $('.par-search-btn').on('click', function(e) {
        e.preventDefault();
        const input = $('.web-search-input');
        const query = input.val().trim();
        if (query !== '') {
            if (!parTaskId) {  // parTaskId가 없을 때만 새로운 PAR 시작
                startPAR(query);
            } else {
                alert('A PAR process is already running. Please wait for it to complete.');
            }
        } else {
            alert('Please enter a search query for Powerful-Auto-Researcher.');
        }
    });

    $('#viewResults').click(function() {
        window.location.href = "/par_search";
    });

    $('#cancelPar').click(function() {
        if (confirm("Are you sure you want to cancel the PAR process?")) {
            socket.emit('cancel_par', { task_id: parTaskId });
            localStorage.removeItem('parTaskId');
            parTaskId = null;
            hideParOverlay();
            updateParButton();
        }
    });

    $('.par-close').click(function() {
        $('#parOverlay').hide();
    });

    $('.par-minimize').click(function() {
        $('#parOverlay').toggleClass('minimized');
    });

    $('#parModalYes').click(function() {
        $('#parModal').hide();
        sendPARInput(true);
    });

    $('#parModalNo').click(function() {
        $('#parModal').hide();
        sendPARInput(false);
    });
});