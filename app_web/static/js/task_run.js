function check_update_task_run() {
    send_ajax(
        `/api/task/${TASK_ID}/run/${TASK_RUN_SEQ}`,
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
    // TODO: Больше полей проверять/обновлять

    let work_status = task_run == null
        ? TASK_RUN_WORK_STATUS
        : task_run.work_status
    ;

    // Завершение интервала для завершенных запусков
    if (
        interval_update_task_run != null
        && work_status != "none" && work_status != "in_processed"
    ) {
        clearInterval(interval_update_task_run);
    }

    $(".task_run_work_status").html(
        get_work_status_task_widget(work_status)
    );
}


$(function() {
    update_task_run();
    // Запуск интервала для не завершенных запусков
    if (TASK_RUN_WORK_STATUS == "none" || TASK_RUN_WORK_STATUS == "in_processed") {
        interval_update_task_run = setInterval(
            check_update_task_run,
            1000 // Каждая секунда
        );
    }

    new DataTable('#table-task-run-logs', {
        ajax: {
            url: `/api/task/${TASK_ID}/run/${TASK_RUN_SEQ}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
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
