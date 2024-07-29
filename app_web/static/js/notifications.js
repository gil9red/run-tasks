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


function send_ajax_create_notification(url, method, data) {
    $.ajax({
        url: url,
        method: method,  // HTTP метод, по умолчанию GET
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        dataType: "json",  // Тип данных загружаемых с сервера
        success: data => on_ajax_success(data, "#table-notifications", update_rows_table_by_response),
        error: data => on_ajax_error(data, 'при создании уведомления'),
    });
}


function actions_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }

    let tags = [];
    if (row.sending_date == null && row.canceling_date == null) {
        let tag = `
            <button
                    class="btn text-warning p-0"
                    title="Отмена уведомления #${row.id}"
                    data-url="/api/notification/${row.id}/do-stop"
                    data-method="POST"
            >
                <i class="bi bi-stop-circle"></i>
            </button>
        `;
        tags.push(tag);
    }
    return tags.join("");
}


$(function() {
    let $unsent_notifications = $("#unsent-notifications");
    if ($unsent_notifications.length) {
        // Доступность кнопки отмены всех уведомлений
        function update_disabled_btn_do_stop_all() {
            $("#btn-do-stop-all").prop(
                "disabled",
                $unsent_notifications.hasClass("d-none")
            );
        }

        update_disabled_btn_do_stop_all();
        setInterval(
            update_disabled_btn_do_stop_all,
            1000 // Каждую 1 секунду
        );
    }

    let $checkbox_all = $("#modal-create-notification-input-is-all");
    let $select_kind = $("#modal-create-notification-input-kind");
    $checkbox_all.on('change', function() {
        let checked = $(this).is(':checked');
        $select_kind.prop("disabled", checked);
    });
    $select_kind.prop(
        "disabled",
        $checkbox_all.is(":checked")
    );

    // Создание уведомления
    let $modal_create_notification = $('#modal-create-notification');

    $modal_create_notification.find("form").submit(function() {
        $modal_create_notification.modal('hide');

        let $this = $(this);

        let url = $this.attr("action");
        let method = $this.attr("method");
        if (method === undefined) {
            method = "get";
        }

        let data = convertFormToJSON(this);

        if ($checkbox_all.is(":checked")) {
            for (let kind of ["telegram", "email"]) {
                data.kind = kind;
                send_ajax_create_notification(url, method, data);
            }
        } else {
            send_ajax_create_notification(url, method, data);
        }

        return false;
    });

    new DataTable('#table-notifications', {
        ajax: {
            url: `/api/notifications`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            {
                data: null, // Явное указание, что тут нет источника данных
                render: actions_render,
                orderable: false,
                title: getTableHeaderTitleWithMenu(), // TODO: Перенести кнопку создания?
                width: '0px',
            },
            { data: 'id', title: 'Ид.', }, // TODO: Спрятать?
            { data: 'task_run', title: 'Ид. запуска', }, // TODO: Спрятать? Заполнять ссылку на запуск (брать task_run_seq)?
            { data: 'name', title: 'Название', },
            { data: 'text', title: 'Текст', },
            { data: 'kind', title: 'Тип', render: kind_render, },
            { data: 'append_date', title: 'Добавлено', render: date_render, },
            { data: 'sending_date', title: 'Отправлено', render: date_render, },
            { data: 'canceling_date', title: 'Отменено', render: date_render, },
        ],
        order: [
            // Сортировка по убыванию id
            [1, "desc"],
        ],
        ...COMMON_PROPS_DATA_TABLE,
    });
});
