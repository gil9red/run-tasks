function is_last_uri() {
    return window.TASK_RUN_SEQ == "last";
}


function check_update_task_run() {
    send_ajax(
        `/api/task/${window.TASK_ID}/run/${window.TASK_RUN_SEQ}`,
        "GET",
        null, // json
        null, // css_selector_table
        (css_selector_table, rs) => {
            update_task_run(rs.result[0]);
        }
    );
}


let interval_update_task_run = null;


function update_task_run(task_run=null) {
    if (task_run != null) {
        if (is_last_uri()) {
            $(".task-run-seq").text(task_run.seq);
            $("title").text(window.PATTERN.title.format(task_run.seq));
            $(".task-run-seq-url").attr("href", window.PATTERN.title.url);

            let btn_send_notification = document.getElementById("btn-send-notification");
            btn_send_notification.title = window.PATTERN.button_send_notification.title.format(task_run.seq);
            btn_send_notification.dataset.url = window.PATTERN.button_send_notification.data_url.format(task_run.seq);

            let btn_stop = document.getElementById("btn-stop");
            btn_stop.title = window.PATTERN.button_stop.title.format(task_run.seq);
            btn_stop.dataset.url = window.PATTERN.button_stop.data_url.format(task_run.seq);
        }

        fill_document_fields(task_run);
    }

    let work_status = task_run == null
        ? window.TASK_RUN_WORK_STATUS
        : task_run.work_status
    ;

    // Завершение интервала для завершенных запусков
    if (
        interval_update_task_run != null
        && !["none", "in_processed"].includes(work_status)
        && !is_last_uri()  // Если это не страница последнего запуска
    ) {
        clearInterval(interval_update_task_run);
        stop_datatables_auto_reload();
    }

    $(".task_run_work_status").html(
        get_work_status_task_widget(work_status, true)
    );
    $("#btn-stop").toggleClass("d-none", work_status != "in_processed");
}


$(function() {
    const tableId = "table-task-run-logs";

    update_task_run();

    // Запуск интервала для не завершенных запусков
    // Или для страницы последней задачи
    let auto_reload = ["none", "in_processed"].includes(window.TASK_RUN_WORK_STATUS)
        || is_last_uri();
    if (auto_reload) {
        interval_update_task_run = setInterval(
            check_update_task_run,
            1000 // Каждая секунда
        );
    } else {
        // Отключение автообновления таблиц из base.js
        DATATABLES_AUTO_RELOAD_STOPPING.push(tableId);
    }

    new DataTable(`#${tableId}`, {
        ajax: {
            url: `/api/task/${TASK_ID}/run/${window.TASK_RUN_SEQ}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
        columnDefs: [
            {
                targets: "_all",
                createdCell: function (td, cellData, rowData, row, col) {
                    // Окрашивание текста строки для ошибок
                    if (rowData.kind == 'err') {
                        $(td).addClass('text-danger');
                    }
                }
            }
        ],
        columns: [
            {
                data: null, // Явное указание, что тут нет источника данных
                render: () => null,
                orderable: false,
                title: getTableHeaderTitleWithMenu(), // TODO: Перенести кнопку создания?
                width: '0px',
            },
            { data: 'id', title: 'Ид.', },
            { data: 'task_run', title: 'Запуск', },
            { data: 'kind', title: 'Тип', },
            { data: 'text', title: 'Текст', },
            { data: 'date', title: 'Дата', render: date_render, },
        ],
        order: [
            // Сортировка по возрастанию id
            [1, "asc"],
        ],
        ...COMMON_PROPS_DATA_TABLE,
    });
});
