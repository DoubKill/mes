var Equip_cate_filter = {

    data: function () {

        return {

            category_name: "",
            equip_type: "",
        }
    },

    methods: {

        category_nameChanged: function () {

            this.getFirstPage();
        },
        equip_typeChanged: function () {

            this.getFirstPage();
        },
        beforeGetData() {

            this.getParams['category_name'] = this.category_name;
            this.getParams['equip_type'] = this.equip_type;
        },
    }
};