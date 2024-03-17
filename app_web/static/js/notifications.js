function kind_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    let icon = data == 'email'
        ? `<i class="bi bi-envelope-fill"></i>`
        : `<i class="bi bi-telegram"></i>`
    ;
    return `<div class="d-flex justify-content-center">${icon}</div>`;
}

$(function() {
    new DataTable('#table-notifications', {
        ajax: {
            url: `/api/notifications`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { data: 'id', title: 'id', },
            { data: 'task_run', title: 'task_run', },
            { data: 'name', title: 'name', },
            { data: 'text', title: 'text', },
            { data: 'kind', title: 'kind', render: kind_render, },
            { data: 'append_date', title: 'append_date', },
            { data: 'sending_date', title: 'sending_date', },
        ],
        order: [
            // Сортировка по возрастанию id
            [0, "asc"],
        ],
    });
});
