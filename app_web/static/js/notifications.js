function kind_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }

    let icon = data;
    switch (data) {
        case "email":
            icon = `<i class="bi bi-envelope-fill"></i>`;
            break;

        case "telegram":
            icon = `<i class="bi bi-telegram"></i>`;
            break;
    }
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
            { data: 'append_date', title: 'append_date', render: date_render, },
            { data: 'sending_date', title: 'sending_date', render: date_render, },
        ],
        order: [
            // Сортировка по возрастанию id
            [0, "asc"],
        ],
        language: LANG_DATATABLES,
    });
});
