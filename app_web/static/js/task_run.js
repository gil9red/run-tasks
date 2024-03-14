function link_to_task_run_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    return `<a href="/task/${row.task}/run/${row.id}"><i class="bi bi-box-arrow-up-right"></i></a>`;
}

$(function() {
    new DataTable('#table-task-run-logs', {
        ajax: {
            url: `/api/task/${TASK_ID}/run/${TASK_RUN_SEQ}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { data: 'id', title: 'id', },
            { data: 'task_run', title: 'task_run', },
            { data: 'kind', title: 'kind', },
            { data: 'text', title: 'text', },
            { data: 'date', title: 'date', },
        ],
        order: [
            // Сортировка по возрастанию id
            [0, "asc"],
        ],
    });
});
