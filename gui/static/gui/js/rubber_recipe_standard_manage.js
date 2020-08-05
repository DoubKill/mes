;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {

            return {

                tableDataUrl: ProductInfosUrl,
                dialogAddRubberRecipe: false,
                originOptions: [],
                rubberRecipeForm: {
                    factory: "",
                    product_no: "",
                    versions: "",
                    product_name: "",
                    precept: ""
                },
                materials: [],
                selectedMaterials: [],
                dialogChoiceMaterials: false,
                dialogRubberRecipeStandard: false,
                selectingMaterial: false,
                carNumberOptionsNotRm: [],
                carNumberOptionsRm: [],
                ratioSum: 0,
                rubberRecipeError: "",
                carNumberIdByName: {},
                currentRow: null,
                materialById: {}
            }
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {
                    class_name: '产地'
                }
            }).then(function (response) {

                app.originOptions = response.data.results;
            }).catch(function (error) {

            });
            axios.get(MaterialsUrl)
                .then(function (response) {

                    app.materials = response.data.results;
                    for (var i = 0; i < app.materials.length; ++i) {

                        app.materialById[Number(app.materials[i].id)] = app.materials[i];
                    }
                }).catch(function (error) {

            });
            axios.get(GlobalCodesUrl, {

                params: {
                    class_name: "车次"
                }
            }).then(function (response) {

                for (var i = 0; i < response.data.results.length; ++i) {

                    app.carNumberIdByName
                        [response.data.results[i].global_name] = response.data.results[i].id;
                    if (response.data.results[i].global_name.startsWith("RM")) {

                        app.carNumberOptionsRm.push(response.data.results[i])
                    } else {

                        app.carNumberOptionsNotRm.push(response.data.results[i])
                    }
                }
            }).catch(function (error) {

            })
        },
        methods: {

            usedTypeFormatter: function (row, column) {

                return this.usedTypeChoice(row.used_type);
            },
            usedTypeChoice: function (usedType) {

                switch (usedType) {

                    case 1:
                        return "编辑";
                    case 2:
                        return "通过";
                    case 3:
                        return "应用";
                    case 4:
                        return "驳回";
                    case 5:
                        return "废弃";
                }
            },
            editButtonText: function (row) {

                switch (row.used_type) {

                    case 1:
                        return "应用";
                    case 3:
                        return "废弃";
                }
            },
            showAddRubberRecipeDialog: function () {

                this.rubberRecipeError = "";
                this.dialogAddRubberRecipe = true;
            },
            handleAddRubberRecipe: function () {

                var app = this;
                this.rubberRecipeError = "";
                axios.get(ValidateVersionsUrl, {

                    params: this.rubberRecipeForm
                }).then(function (response) {

                    if (response.data.code === 0) {


                        app.dialogAddRubberRecipe = false;
                        app.dialogChoiceMaterials = true

                    } else {

                        app.rubberRecipeError = response.data.message
                    }
                }).catch(function (error) {

                    app.rubberRecipeError = error.response.data.join(",");
                });
            },
            handleMaterialsSelectionChange: function (val) {

                this.selectingMaterial = true;
                for (var i = 0; i < val.length; ++i) {

                    if (this.selectedMaterials.indexOf(val[i]) === -1) {

                        this.selectedMaterials.push(val[i])
                    }
                }
                for (var j = 0; j < this.selectedMaterials.length; ++j) {

                    if (this.selectedMaterials[j].id && val.indexOf(this.selectedMaterials[j]) === -1) {

                        this.selectedMaterials.splice(j, 1);
                        --j;
                    }
                }
                var app = this;
                setTimeout(function () {

                    if (val) {
                        val.forEach(row => {
                            app.$refs.materialsMultipleTable.toggleRowSelection(row, true);
                        });
                    }
                    app.selectingMaterial = false;
                }, 0);

            },
            handleSelectedMaterialsSelectionChange: function (val) {

                if (this.selectingMaterial)
                    return;
                for (var i = 0; i < this.materials.length; ++i) {

                    var material = this.materials[i];
                    if (val.indexOf(material) === -1) {

                        this.$refs.allMaterialsMultipleTable.toggleRowSelection(material, false);
                    }
                }
                if (!val.length) {

                    for (var j = 0; j < this.selectedMaterials.length; ++j) {

                        if (!this.selectedMaterials[j].id) {

                            this.selectedMaterials.splice(j, 1);
                            --j;
                        }
                    }
                }
            },
            rmClicked: function () {

                var emptyRow = {};
                this.selectedMaterials.push(emptyRow);
                var app = this;
                app.$refs.materialsMultipleTable.toggleRowSelection(app.selectedMaterials[app.selectedMaterials.length - 1], true);
            },
            handleSelect: function (selection, row) {

                if (!row.id) {
                    this.selectedMaterials.splice(this.selectedMaterials.indexOf(row), 1)
                }
            },

            initRatio() {

                for (var i = 0; i < this.selectedMaterials.length; ++i) {

                    if (this.selectedMaterials[i].car_number.indexOf('RM') !== 0 && !this.selectedMaterials[i].ratio) {

                        Vue.set(this.selectedMaterials[i], 'ratio', 0.0)
                    }
                    if (!this.selectedMaterials[i].ratio_sum) {


                        Vue.set(this.selectedMaterials[i], 'ratio_sum', 0.0)
                    }

                }
            },

            selectClicked: function () {

                if (!this.selectedMaterials.length)
                    return;
                this.initRatio();
                this.carNumberChanged();
                this.dialogChoiceMaterials = false;
                this.dialogRubberRecipeStandard = true;
            },
            newClicked: function () {

                this.dialogRubberRecipeStandard = false;
                this.dialogChoiceMaterials = true;

            },
            saveClicked: function () {

                var rubberRatioSum = 0.0;
                for (var i = 0; i < this.selectedMaterials.length; ++i) {

                    if (this.selectedMaterials[i].material_type_name && (
                        this.selectedMaterials[i].material_type_name === "天然胶"
                        || this.selectedMaterials[i].material_type_name === "合成胶")) {

                        rubberRatioSum += this.selectedMaterials[i].ratio
                    }
                }
                if (rubberRatioSum !== 100.0) {

                    this.$alert('天然胶加合成胶总配比必须为100', '警告', {
                        confirmButtonText: '确定',
                    });
                } else {
                    var app = this;
                    var productrecipe_set = [];
                    for (i = 0; i < this.selectedMaterials.length; ++i) {

                        var productrecipe = {

                            stage: app.carNumberIdByName[app.selectedMaterials[i].car_number],
                            num: i,
                            ratio: app.selectedMaterials[i].ratio,
                        };
                        if (this.selectedMaterials[i].id) {

                            productrecipe.material = this.selectedMaterials[i].id;
                        }
                        productrecipe_set.push(productrecipe)
                    }
                    axios.post(ProductInfosUrl, {

                        product_no: app.rubberRecipeForm.product_no,
                        product_name: app.rubberRecipeForm.product_name,
                        versions: app.rubberRecipeForm.versions,
                        precept: app.rubberRecipeForm.precept,
                        factory: app.rubberRecipeForm.factory,
                        productrecipe_set: productrecipe_set
                    }).then(function (response) {

                        app.dialogRubberRecipeStandard = false;
                        app.$message(app.rubberRecipeForm.product_name + "创建成功");
                        app.currentChange(app.currentPage);

                    }).catch(function (error) {

                        this.$message({
                            message: error.response.data,
                            type: 'error'
                        });
                    });
                }
            },
            carNumberChanged: function () {

                for (var i = 0; i < this.selectedMaterials.length; ++i) {

                    if (!this.selectedMaterials[i - 1]) { // 第一项

                        this.selectedMaterials[i].ratio_sum = this.selectedMaterials[i].ratio;
                    } else if (this.selectedMaterials[i].ratio) { // 非rm

                        this.selectedMaterials[i].ratio_sum =
                            this.selectedMaterials[i].ratio + this.selectedMaterials[i - 1].ratio_sum;
                    } else { // rm
                        this.selectedMaterials[i].ratio_sum = this.selectedMaterials[i - 1].ratio_sum;
                    }

                    this.selectedMaterials[i].ratio_sum = Number(this.selectedMaterials[i].ratio_sum.toFixed(2));
                }
                this.ratioSum = this.selectedMaterials[this.selectedMaterials.length - 1].ratio_sum;
            },
            handleCurrentChange: function (val) {

                this.currentRow = val;
            },
            showRecipeClicked: function () {

                if (!this.currentRow)
                    return;
                var app = this;
                axios.get(ProductInfosUrl + this.currentRow.id + "/")
                    .then(function (response) {

                        app.selectedMaterials = [];
                        for (var i = 0; i < response.data.productrecipe_set.length; ++i) {

                            var material_no = app.materialById[response.data.productrecipe_set[i].material] ?
                                app.materialById[response.data.productrecipe_set[i].material].material_no : null
                            app.selectedMaterials.push({
                                id: response.data.productrecipe_set[i].material,
                                car_number: response.data.productrecipe_set[i].stage_name,
                                material_type_name: response.data.productrecipe_set[i].material_material_type,
                                material_name: response.data.productrecipe_set[i].material_name,
                                material_no,
                                ratio: Number(response.data.productrecipe_set[i].ratio)
                            });
                        }
                        if (app.selectedMaterials.length) {

                            app.initRatio();
                            app.carNumberChanged();
                        }
                        app.dialogRubberRecipeStandard = true;

                    }).catch(function (error) {

                });

            },
            dialogChoiceMaterialsOpen() {

                if (this.selectedMaterials.length) {

                    var app = this;
                    setTimeout(function () {

                        console
                        console.log(app.materials);
                        for (var i = 0; i < app.selectedMaterials.length; ++i) {


                            app.$refs.materialsMultipleTable.toggleRowSelection(app.selectedMaterials[i], true);



                        }
                    }, 0);
                }
            },
            // toggleRowSelection: function () {
            //
            //     for (i = 0; i < this.selectedMaterials.length; ++i) {
            //
            //         this.$refs.materialsMultipleTable
            //             .toggleRowSelection(app.selectedMaterials[i], true);
            //     }
            // }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();