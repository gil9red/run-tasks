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
    // Создание уведомления
    let $modal_create_notification = $('#modal-create-notification');

    $modal_create_notification.find("form").submit(function() {
        $modal_create_notification.modal('hide');

        let thisForm = this;

        let url = $(this).attr("action");
        let method = $(this).attr("method");
        if (method === undefined) {
            method = "get";
        }

        $.ajax({
            url: url,
            method: method,  // HTTP метод, по умолчанию GET
            data: JSON.stringify(convertFormToJSON(this)),
            contentType: "application/json; charset=utf-8",
            dataType: "json",  // Тип данных загружаемых с сервера
            success: function(data) {
                on_ajax_success(data, "#table-notifications", update_rows_table_by_response);

                // Очищение полей формы
                thisForm.reset();
            },
            error: data => on_ajax_error(data, 'при создании уведомления'),
        });

        return false;
    });

    new DataTable('#table-notifications', {
        ajax: {
            url: `/api/notifications`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            { data: 'id', title: 'Ид.', }, // TODO: Спрятать?
            { data: 'task_run', title: 'Ид. запуска', }, // TODO: Спрятать? Заполнять ссылку на запуск (брать task_run_seq)?
            { data: 'name', title: 'Название', },
            { data: 'text', title: 'Текст', },
            { data: 'kind', title: 'Тип', render: kind_render, },
            { data: 'append_date', title: 'Добавлено', render: date_render, },
            { data: 'sending_date', title: 'Отправлено', render: date_render, },
        ],
        order: [
            // Сортировка по убыванию id
            [0, "desc"],
        ],
        language: LANG_DATATABLES,
    });
});
