var Equip_cate_filter = {

    data: function () {

        return {

            category_name: "",
            equip_type_name: "",
        }
    },

    methods: {

        category_nameChanged: function () {

            this.getFirstPage();
        },
        equip_type_nameChanged: function () {

            this.getFirstPage();
        },
        beforeGetData() {

            this.getParams['category_name'] = this.category_name;
            this.getParams['equip_type_name'] = this.equip_type_name;
        },
    }
};