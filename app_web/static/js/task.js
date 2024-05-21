function actions_task_run_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }

    let tags = [
        `
        <a class="icon-link" href="/task/${row.task}/run/${row.seq}">
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
        `,
        `
        <button
                class="btn text-danger p-0"
                title="Отправить уведомления запуска #${row.seq}"
                data-url="/api/task/${row.task}/run/${row.seq}/do-send-notifications"
                data-method="POST"
        >
            <i class="bi bi-send"></i>
        </button>
        `
    ];
    if (row.work_status == "in_processed") {
        let tag = `
            <button
                    class="btn text-warning p-0"
                    title="Остановить запуск #${row.seq}"
                    data-url="/api/task/${row.task}/run/${row.seq}/do-stop"
                    data-method="POST"
            >
                <i class="bi bi-stop-circle"></i>
            </button>
        `;
        tags.push(tag);
        $("#btn-stop").html(tag);
    }
    return tags.join("");
}


function check_update_task() {
    send_ajax(
        `/api/task/${TASK_ID}`,
        "GET",
        null, // json
        null, // css_selector_table
        (css_selector_table, rs) => {
            update_task(rs.result[0]);
        }
    );
}


function update_task(task=null) {
    // TODO: Больше полей проверять/обновлять

    let last_work_status = task == null
        ? TASK_LAST_WORK_STATUS
        : task.last_work_status
    ;

    $(".task_last_work_status").html(
        get_work_status_task_widget(last_work_status)
    );

    // Не показывать кнопку запуска задачи, если она запущена
    $("#btn-do-run").toggleClass("d-none", last_work_status == "in_processed");

    $("#btn-stop").toggleClass("d-none", last_work_status != "in_processed");
}


$(function() {
    update_task();
    setInterval(
        check_update_task,
        1000 // Каждая секунда
    );

    new DataTable('#table-task-runs', {
        ajax: {
            url: `/api/task/${TASK_ID}/runs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            {
                data: null, // Явное указание, что тут нет источника данных
                render: actions_task_run_render,
                orderable: false,
                title: getTableHeaderTitleWithMenu(),
                width: '10px',
            },
            {
                data: 'work_status',
                render: work_status_task_run_render,
                orderable: false,
                title: 'Статус',
            },
            { data: 'id', title: 'Ид.', visible: false, },
            { data: 'task', title: 'Задача', visible: false, },
            { data: 'seq', title: '#', },
            { data: 'command', title: 'Команда', },
            { data: 'status', title: 'Статус БД', visible: false, },
            { data: 'process_id', title: 'Ид. процесса', visible: false, },
            { data: 'process_return_code', title: 'Код возврата процесса', visible: false, },
            { data: 'create_date', title: 'Создано', render: date_render, visible: false, },
            { data: 'start_date', title: 'Запущено', render: date_render, },
            { data: 'finish_date', title: 'Завершено', render: date_render, },
            { data: 'scheduled_date', title: 'Запланировано', render: date_render, visible: false, },
        ],
        order: [
            // Сортировка по убыванию seq
            [4, "desc"],
        ],
        ...COMMON_PROPS_DATA_TABLE,
    });
});
