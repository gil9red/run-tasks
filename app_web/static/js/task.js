function actions_task_run_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    return `
        <a href="/task/${row.task}/run/${row.seq}">
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
    `;
}


$(function() {
    $(".task_last_work_status").html(
        get_work_status_task_widget(TASK_LAST_WORK_STATUS)
    );

    new DataTable('#table-task-runs', {
        ajax: {
            url: `/api/task/${TASK_ID}/runs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            { render: actions_task_run_render, orderable: false, },
            { data: 'id', title: 'Ид.', },
            { data: 'task', title: 'Задача', },
            { data: 'seq', title: '#', },
            { data: 'command', title: 'Команда', },
            { data: 'status', title: 'Статус', },
            { data: 'process_id', title: 'Ид. процесса', },
            { data: 'process_return_code', title: 'Код возврата процесса', },
            { data: 'create_date', title: 'Создано', render: date_render, },
            { data: 'start_date', title: 'Запущено', render: date_render, },
            { data: 'finish_date', title: 'Завершено', render: date_render, },
            { data: 'scheduled_date', title: 'Запланировано', render: date_render, },
        ],
        order: [
            // Сортировка по убыванию id
            [1, "desc"],
        ],
        initComplete: tableInitComplete,
        language: LANG_DATATABLES,
    });
});
