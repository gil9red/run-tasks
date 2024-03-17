function link_to_task_run_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    return `
        <a href="/task/${row.task}/run/${row.seq}" target=”_blank”>
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
    `;
}

$(function() {
    new DataTable('#table-task-runs', {
        ajax: {
            url: `/api/task/${TASK_ID}/runs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { render: link_to_task_run_render, orderable: false, },
            { data: 'id', title: 'id', },
            { data: 'task', title: 'task', },
            { data: 'seq', title: 'seq', },
            { data: 'command', title: 'Команда', },
            { data: 'status', title: 'Статус', },
            { data: 'process_id', title: 'process_id', },
            { data: 'process_return_code', title: 'process_return_code', },
            { data: 'create_date', title: 'create_date', },
            { data: 'start_date', title: 'start_date', },
            { data: 'finish_date', title: 'finish_date', },
            { data: 'scheduled_date', title: 'scheduled_date', },
        ],
        order: [
            // Сортировка по убыванию id
            [1, "desc"],
        ],
    });
});
