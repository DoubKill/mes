var GroupsFilterMixin = {

    data: function () {

        return {

            group_code: "",
            name: "",
        }
    },

    methods: {

        groupCodeChanged: function () {

            this.getFirstPage();
        },
        nameChanged: function () {

            this.getFirstPage();
        },
        beforeGetData() {

            this.getParams['group_code'] = this.group_code;
            this.getParams['name'] = this.name;
        },
    }
};