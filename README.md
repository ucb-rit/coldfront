# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ucb-rit/coldfront/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                                        |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| coldfront/\_\_init\_\_.py                                                                                   |        8 |        3 |        0 |        0 |     62% |      9-11 |
| coldfront/api/allocation/filters.py                                                                         |       37 |        0 |        0 |        0 |    100% |           |
| coldfront/api/allocation/serializers.py                                                                     |      100 |        0 |       22 |        1 |     99% | 189-\>194 |
| coldfront/api/allocation/urls.py                                                                            |       24 |        0 |        0 |        0 |    100% |           |
| coldfront/api/allocation/views.py                                                                           |      103 |        0 |       12 |        4 |     97% |58-\>61, 88-\>91, 117-\>120, 135-\>138 |
| coldfront/api/billing/serializers.py                                                                        |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/api/billing/urls.py                                                                               |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/api/billing/views.py                                                                              |       14 |        0 |        0 |        0 |    100% |           |
| coldfront/api/permissions.py                                                                                |       29 |        1 |       12 |        1 |     95% |        59 |
| coldfront/api/project/filters.py                                                                            |       48 |        3 |        8 |        2 |     91% |42-\>39, 44-45, 51 |
| coldfront/api/project/serializers.py                                                                        |       36 |        0 |        4 |        0 |    100% |           |
| coldfront/api/project/urls.py                                                                               |       12 |        0 |        0 |        0 |    100% |           |
| coldfront/api/project/views.py                                                                              |       53 |        1 |        4 |        1 |     96% |        94 |
| coldfront/api/resource/serializers.py                                                                       |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/api/statistics/pagination.py                                                                      |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/api/statistics/serializers.py                                                                     |      140 |       18 |       34 |        7 |     84% |33-34, 75, 78-79, 101-104, 156-159, 170-172, 205-\>221, 207-211, 227-\>238, 229-232 |
| coldfront/api/statistics/urls.py                                                                            |        9 |        0 |        0 |        0 |    100% |           |
| coldfront/api/statistics/utils.py                                                                           |      168 |       27 |       46 |       19 |     79% |59, 61, 87, 89, 137, 139, 141, 193, 226, 279, 281, 284-287, 310, 312, 315-318, 345, 347, 349, 380, 382, 384 |
| coldfront/api/statistics/views.py                                                                           |      305 |       19 |       54 |        5 |     93% |138, 145-146, 161-162, 166-\>172, 169-170, 191-192, 290-295, 304-309, 440, 636-639, 650-652 |
| coldfront/api/urls.py                                                                                       |        8 |        0 |        2 |        1 |     90% | 21-\>exit |
| coldfront/api/user/authentication.py                                                                        |       20 |        2 |        4 |        2 |     83% |    20, 23 |
| coldfront/api/user/filters.py                                                                               |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/api/user/serializers.py                                                                           |       40 |        0 |        2 |        0 |    100% |           |
| coldfront/api/user/urls.py                                                                                  |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/api/user/views.py                                                                                 |      106 |       25 |       24 |        1 |     75% |48-73, 201-\>217 |
| coldfront/api/utils/urls.py                                                                                 |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/core/account/adapter.py                                                                           |       10 |        5 |        4 |        0 |     36% |     14-18 |
| coldfront/core/account/admin.py                                                                             |       45 |        5 |       12 |        0 |     91% |     49-56 |
| coldfront/core/account/apps.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/account/urls.py                                                                              |       13 |        0 |        8 |        0 |    100% |           |
| coldfront/core/account/utils/login\_activity.py                                                             |       47 |        3 |        4 |        2 |     90% | 61-62, 79 |
| coldfront/core/account/utils/queries.py                                                                     |       34 |        8 |        8 |        0 |     81% |     27-34 |
| coldfront/core/allocation/admin.py                                                                          |      262 |       93 |       44 |        0 |     55% |93, 96, 99, 102-105, 108-112, 115-119, 122-128, 152, 162-172, 194-197, 200, 203, 206-207, 213, 216, 219-222, 225-229, 232-236, 261, 264, 267, 270-271, 274, 277-280, 283-287, 290-294, 297, 301, 306, 328, 337-347, 362, 365, 368-369, 401, 404, 407-408, 414, 417, 420, 423-426, 429-433, 448, 451, 454, 468 |
| coldfront/core/allocation/apps.py                                                                           |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/forms.py                                                                          |      173 |       36 |       24 |        5 |     72% |43-68, 87-92, 125-126, 206-207, 265-266, 274-275, 286, 293-\>296, 309-314, 326 |
| coldfront/core/allocation/forms\_/secure\_dir\_forms.py                                                     |       79 |        3 |       10 |        4 |     92% |19-\>23, 28, 91, 196 |
| coldfront/core/allocation/management/commands/add\_allocation\_defaults.py                                  |       26 |        0 |       16 |        0 |    100% |           |
| coldfront/core/allocation/management/commands/add\_directory\_defaults.py                                   |       34 |        0 |        4 |        0 |    100% |           |
| coldfront/core/allocation/management/commands/approve\_renewal\_requests\_for\_allocation\_period.py        |       80 |        4 |       14 |        1 |     95% |97, 116-121 |
| coldfront/core/allocation/management/commands/audit\_allocation\_period.py                                  |      173 |      123 |       34 |        0 |     24% |34-38, 47-87, 94-113, 128-130, 138-140, 143-145, 149-151, 154-168, 173-181, 187-208, 213, 216-218, 221-229, 234, 242, 245-250, 255-270, 273, 281-286, 292-305, 308-310, 313-318 |
| coldfront/core/allocation/management/commands/convert\_cluster\_attributes\_to\_cluster\_access\_request.py |       61 |       61 |       26 |        0 |      0% |     1-164 |
| coldfront/core/allocation/management/commands/correct\_user\_service\_units.py                              |       68 |       68 |       12 |        0 |      0% |     1-124 |
| coldfront/core/allocation/management/commands/create\_allocation\_periods.py                                |       72 |       20 |       22 |        4 |     70% |44-45, 52-75, 86, 89, 106-\>113 |
| coldfront/core/allocation/management/commands/load\_allocation\_renewal\_requests.py                        |      208 |      208 |       38 |        0 |      0% |     1-403 |
| coldfront/core/allocation/management/commands/parse\_academic\_calendar.py                                  |       60 |       60 |       18 |        0 |      0% |     1-160 |
| coldfront/core/allocation/management/commands/schedule\_allocation\_period\_audits.py                       |      106 |      106 |       20 |        0 |      0% |     1-240 |
| coldfront/core/allocation/management/commands/send\_allowance\_renewal\_available\_emails.py                |       42 |       42 |        8 |        0 |      0% |      1-73 |
| coldfront/core/allocation/management/commands/set\_allocation\_renewal\_request\_computing\_allowances.py   |       30 |       30 |        4 |        0 |      0% |      1-55 |
| coldfront/core/allocation/management/commands/start\_allocation\_period.py                                  |      174 |       21 |       40 |        3 |     89% |157, 261-\>271, 277-283, 288-294, 299-305, 316-320, 341 |
| coldfront/core/allocation/models.py                                                                         |      443 |       85 |       92 |        8 |     75% |77-97, 112, 120, 132-148, 151, 164, 167-171, 174-189, 192-194, 206, 216, 224, 241, 262-267, 296, 311, 323, 348-360, 390-409, 533, 610-612, 620, 655, 679, 703, 762, 768, 798, 822 |
| coldfront/core/allocation/signals.py                                                                        |       21 |        1 |        8 |        1 |     93% |        43 |
| coldfront/core/allocation/signals\_/renewal\_signals.py                                                     |       27 |        0 |        2 |        0 |    100% |           |
| coldfront/core/allocation/tasks.py                                                                          |       69 |       69 |       28 |        0 |      0% |     1-187 |
| coldfront/core/allocation/urls.py                                                                           |       15 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils.py                                                                          |      127 |       31 |       36 |        5 |     72% |43-46, 51-75, 79-87, 91-102, 210, 212, 214, 216, 274 |
| coldfront/core/allocation/utils\_/accounting\_utils/\_\_init\_\_.py                                         |      136 |        2 |       30 |        9 |     93% |110-\>114, 154-\>exit, 204-205, 214-\>220, 264-\>exit, 274-\>exit, 366-\>368, 372-\>377, 415-\>417, 428-\>433 |
| coldfront/core/allocation/utils\_/accounting\_utils/domain.py                                               |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils\_/accounting\_utils/services/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils\_/accounting\_utils/services/service\_units\_usage\_service.py              |       60 |        2 |       12 |        0 |     97% |     45-46 |
| coldfront/core/allocation/utils\_/cluster\_access\_utils.py                                                 |      212 |       12 |       18 |        5 |     93% |105-106, 128-132, 164, 223-224, 304, 346-347, 389-\>exit, 415-\>exit, 443 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/\_\_init\_\_.py                                        |       55 |        4 |       20 |        1 |     91% |27, 143-148 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/new\_directory.py                                      |      312 |       47 |       56 |       20 |     81% |63, 65, 67, 78, 105, 152, 251-255, 280-286, 303, 325-\>328, 342-348, 379-386, 398-406, 432, 460-\>463, 477-483, 541, 553-555, 563, 567, 575, 616-619, 627-629, 636-637, 646, 684, 686 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/user\_management.py                                    |      106 |        7 |        8 |        3 |     91% |43, 45, 108, 125-129, 217 |
| coldfront/core/allocation/views.py                                                                          |      953 |      670 |      328 |       31 |     25% |65-\>74, 78, 98, 111-120, 127-130, 143-158, 161, 164, 171, 180, 187, 224-341, 351-358, 360-365, 380, 392-423, 438-480, 521-527, 533-538, 548, 560, 565, 573, 578, 583, 591, 596-598, 603-607, 628-632, 635-636, 640-641, 647, 660-661, 675-687, 691-704, 707-738, 742-744, 747-834, 837, 845-851, 855-868, 871-892, 895-908, 911-954, 962-968, 972-985, 988-1007, 1010-1023, 1026-1066, 1078-1081, 1085-1089, 1092-1096, 1100-1102, 1105, 1113-1116, 1121-1133, 1136-1150, 1153-1183, 1192-1195, 1199-1204, 1212-1215, 1219-1268, 1276-1279, 1283-1326, 1334-1348, 1351-1374, 1377-1395, 1398-1417, 1420-1509, 1519-1527, 1531-1533, 1543-1547, 1550-1563, 1566-1583, 1593-1597, 1600-1604, 1609-1616, 1619, 1629-1633, 1636, 1644-1648, 1652-1661, 1664-1674, 1678-1698, 1709-1718, 1721-1725, 1728-1736, 1739, 1750-1759, 1762 |
| coldfront/core/allocation/views\_/cluster\_access\_views.py                                                 |      286 |       91 |       68 |       22 |     63% |40-41, 45-61, 64-100, 103-124, 138-143, 156-\>182, 160, 166, 172, 178, 192-194, 206-210, 213-214, 218-219, 243-244, 249-250, 271-273, 281-283, 313-315, 339-342, 350-352, 388-\>392, 390, 395-397, 400-\>402, 418, 434-436, 444-446, 476-\>480, 478 |
| coldfront/core/allocation/views\_/secure\_dir\_views/new\_directory/approval\_views.py                      |      458 |       41 |       82 |       18 |     89% |63-68, 111, 116-120, 128, 196-199, 208-215, 317-319, 322-324, 329-332, 343-344, 350, 390, 461, 542, 564-\>566, 616, 638, 682, 690-\>695, 696-\>701, 702-\>707, 708-\>712, 769-771 |
| coldfront/core/allocation/views\_/secure\_dir\_views/new\_directory/request\_views.py                       |      146 |       19 |       14 |        2 |     87% |60-64, 70-74, 88-89, 92-93, 96-98, 178-181, 272-273 |
| coldfront/core/allocation/views\_/secure\_dir\_views/user\_management/approval\_views.py                    |      278 |       32 |       72 |       16 |     85% |65-70, 90-\>113, 94, 98, 102, 108, 125-129, 133-134, 139-140, 147, 167-168, 197, 279, 330-334, 367, 411-\>414, 469-473, 483, 527-\>530 |
| coldfront/core/allocation/views\_/secure\_dir\_views/user\_management/request\_views.py                     |      115 |       11 |       20 |        3 |     88% |59-61, 119-122, 131-132, 151-\>149, 191-192 |
| coldfront/core/billing/admin.py                                                                             |       13 |        1 |        0 |        0 |     92% |        15 |
| coldfront/core/billing/forms.py                                                                             |       81 |       22 |       10 |        1 |     68% |21, 33-\>exit, 81-82, 98-104, 109-116, 133-138 |
| coldfront/core/billing/management/commands/billing\_ids.py                                                  |      236 |       56 |       52 |        1 |     73% |138-139, 148-149, 159-160, 183-185, 195-252, 274-\>exit, 346-348 |
| coldfront/core/billing/models.py                                                                            |       20 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/urls.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/\_\_init\_\_.py                                                                |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/billing\_activity\_managers.py                                                 |      130 |        9 |       10 |        0 |     94% |65, 71, 76, 82, 105, 111, 129, 170, 208 |
| coldfront/core/billing/utils/queries.py                                                                     |      132 |       40 |       36 |        4 |     64% |64, 69-\>74, 114-\>118, 171-229, 259 |
| coldfront/core/billing/utils/validation/\_\_init\_\_.py                                                     |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/validation/backends/base.py                                                    |        6 |        1 |        0 |        0 |     83% |        12 |
| coldfront/core/billing/utils/validation/backends/dummy.py                                                   |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/validation/backends/oracle.py                                                  |       14 |       14 |        0 |        0 |      0% |      1-27 |
| coldfront/core/billing/utils/validation/backends/permissive.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/views/admin\_views.py                                                                |      225 |      168 |       56 |        0 |     20% |43, 46-71, 74, 88-92, 95, 98-104, 107-143, 146-149, 152-157, 160-171, 174-176, 190-208, 218-219, 222-315, 323, 326-349, 353 |
| coldfront/core/field\_of\_science/\_\_init\_\_.py                                                           |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/admin.py                                                                  |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/apps.py                                                                   |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/management/commands/import\_field\_of\_science\_data.py                   |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/core/field\_of\_science/models.py                                                                 |       14 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/tests.py                                                                  |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/core/field\_of\_science/views.py                                                                  |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/core/grant/admin.py                                                                               |       19 |       19 |        2 |        0 |      0% |      1-33 |
| coldfront/core/grant/apps.py                                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/grant/forms.py                                                                               |       17 |       17 |        0 |        0 |      0% |      1-30 |
| coldfront/core/grant/models.py                                                                              |       42 |       42 |        2 |        0 |      0% |      1-73 |
| coldfront/core/grant/tests.py                                                                               |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/core/grant/urls.py                                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/grant/views.py                                                                               |      133 |      133 |       40 |        0 |      0% |     1-252 |
| coldfront/core/portal/admin.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/portal/apps.py                                                                               |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/portal/models.py                                                                             |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/portal/templatetags/portal\_tags.py                                                          |        9 |        1 |        0 |        0 |     89% |        14 |
| coldfront/core/portal/utils.py                                                                              |       37 |       31 |        4 |        0 |     15% |8-32, 37-42, 48-77, 82-112 |
| coldfront/core/portal/views.py                                                                              |       99 |       41 |       14 |        2 |     60% |77-78, 125, 130-131, 137-199, 205-226, 232-249 |
| coldfront/core/project/\_\_init\_\_.py                                                                      |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/admin.py                                                                             |      114 |       32 |       16 |        0 |     63% |61, 64, 67-70, 73-77, 80-84, 131-132, 138-141, 144-148, 151-155, 158-164, 173-174, 180, 188 |
| coldfront/core/project/apps.py                                                                              |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/forms.py                                                                             |      130 |       18 |       12 |        2 |     85% |63-64, 72-84, 101-124, 241, 265-\>exit |
| coldfront/core/project/forms\_/new\_project\_forms/approval\_forms.py                                       |       69 |       41 |       18 |        1 |     33% |29-\>exit, 75-79, 82-90, 93-105, 148-151, 154-162, 165-176 |
| coldfront/core/project/forms\_/new\_project\_forms/request\_forms.py                                        |      314 |       25 |       90 |       16 |     88% |76, 79, 91, 103-\>105, 114, 132-\>134, 257, 292, 296-297, 333-335, 537, 586-\>598, 609-613, 654-\>exit, 666, 674, 917-923 |
| coldfront/core/project/forms\_/removal\_forms.py                                                            |       21 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/forms\_/renewal\_forms/approval\_forms.py                                            |       14 |        0 |        2 |        1 |     94% | 27-\>exit |
| coldfront/core/project/forms\_/renewal\_forms/request\_forms.py                                             |      152 |       13 |       28 |        5 |     88% |72-\>99, 166, 172, 232-239, 254-255, 262-263, 603-614 |
| coldfront/core/project/management/commands/add\_default\_project\_choices.py                                |       19 |        0 |       12 |        0 |    100% |           |
| coldfront/core/project/management/commands/add\_service\_units\_to\_project.py                              |       62 |        0 |        8 |        0 |    100% |           |
| coldfront/core/project/management/commands/deactivate\_ica\_projects.py                                     |       60 |        3 |       10 |        0 |     96% |   116-118 |
| coldfront/core/project/management/commands/pending\_join\_request\_reminder.py                              |       56 |        6 |       12 |        2 |     88% |43-\>34, 84-86, 97-\>88, 126-128 |
| coldfront/core/project/management/commands/projects.py                                                      |      223 |       72 |       36 |        3 |     63% |64, 65-\>exit, 143-189, 193-218, 308-310, 326-384, 439-440, 478 |
| coldfront/core/project/management/commands/set\_new\_project\_request\_allocation\_periods.py               |       84 |       84 |       26 |        0 |      0% |     1-173 |
| coldfront/core/project/management/commands/set\_new\_project\_request\_computing\_allowances.py             |       30 |       30 |        4 |        0 |      0% |      1-55 |
| coldfront/core/project/management/commands/set\_new\_project\_request\_times.py                             |       19 |       19 |        6 |        0 |      0% |      1-49 |
| coldfront/core/project/models.py                                                                            |      281 |       40 |       42 |        7 |     83% |60, 64, 83-90, 106, 118, 128, 239, 248, 255, 283, 328-329, 342, 501, 517-526, 556, 587-605, 623 |
| coldfront/core/project/signals.py                                                                           |       38 |       15 |        0 |        0 |     61% |31-34, 39-46, 60-68 |
| coldfront/core/project/templatetags/iso8601\_to\_datetime.py                                                |       11 |        0 |        2 |        0 |    100% |           |
| coldfront/core/project/urls.py                                                                              |       34 |        0 |        2 |        1 |     97% | 292-\>306 |
| coldfront/core/project/utils.py                                                                             |      114 |       12 |       20 |        7 |     86% |58, 74-\>78, 91, 122, 138-\>142, 153, 197-\>200, 236-243 |
| coldfront/core/project/utils\_/addition\_utils.py                                                           |      118 |        7 |        6 |        1 |     94% |48, 54, 173-175, 220-221 |
| coldfront/core/project/utils\_/email\_utils.py                                                              |        7 |        1 |        2 |        1 |     78% |        24 |
| coldfront/core/project/utils\_/new\_project\_user\_utils.py                                                 |      214 |       11 |       54 |        2 |     95% |66-68, 181, 204-208, 225-229, 410 |
| coldfront/core/project/utils\_/new\_project\_utils.py                                                       |      372 |       76 |       82 |       25 |     74% |76-\>79, 79-\>81, 105-\>109, 128-\>131, 158-160, 179, 215-216, 249, 261, 297-298, 326-\>328, 343-345, 365-372, 382, 395, 425, 428-429, 444-447, 476, 479-480, 495-498, 533, 568, 571-572, 600-629, 637, 640-643, 675, 678-679, 717, 723-744, 752, 760, 770 |
| coldfront/core/project/utils\_/permissions\_utils.py                                                        |        8 |        2 |        4 |        2 |     67% |     9, 11 |
| coldfront/core/project/utils\_/removal\_utils.py                                                            |      174 |        6 |       28 |        3 |     96% |102-\>exit, 198-199, 271, 314-\>327, 364-368 |
| coldfront/core/project/utils\_/renewal\_survey/\_\_init\_\_.py                                              |       16 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/utils\_/renewal\_survey/backends/base.py                                             |       12 |        3 |        0 |        0 |     75% |26, 47, 69 |
| coldfront/core/project/utils\_/renewal\_survey/backends/permissive.py                                       |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/utils\_/renewal\_utils.py                                                            |      555 |      125 |      100 |       24 |     75% |109, 159-167, 179-197, 206, 213, 215, 264-\>269, 269-\>271, 288-323, 335, 365, 397, 425, 463-497, 506, 541, 562-565, 580, 610, 627-629, 655, 673-696, 703-716, 721-726, 732-738, 746-751, 765, 772, 782, 804-806, 822-\>exit, 828, 832, 837, 843, 848, 853, 886, 890, 895, 901, 906, 911, 920-921, 1060-1063, 1067-1073, 1083-1086, 1105, 1123-1124 |
| coldfront/core/project/utils\_/request\_processing\_utils.py                                                |       58 |        0 |       26 |        0 |    100% |           |
| coldfront/core/project/views.py                                                                             |      771 |      426 |      252 |       29 |     40% |69-\>78, 129, 189, 209-212, 234-\>241, 294-302, 325-330, 353-359, 363, 372, 377, 381, 385-393, 415-416, 421-422, 426-427, 447-448, 486-487, 491-553, 557-605, 613-617, 628-635, 638-651, 661-662, 668-680, 683, 697, 701-\>exit, 710-711, 727-736, 746, 749-752, 761-770, 780, 783-841, 853-859, 880-954, 975-1006, 1032, 1042-1052, 1061-1067, 1075-1095, 1103-1112, 1115-1151, 1154-1236, 1241-1257, 1265-1276, 1280-1296, 1299-1308, 1311-1344, 1361, 1366, 1376, 1381, 1409, 1414, 1427-\>1429, 1432-1458, 1461 |
| coldfront/core/project/views\_/addition\_views/approval\_views.py                                           |      285 |       29 |       36 |        3 |     89% |114-117, 126-133, 199-201, 220-222, 273-278, 347, 359, 390-392, 489-\>491, 499-501 |
| coldfront/core/project/views\_/addition\_views/request\_views.py                                            |      151 |       10 |       18 |        0 |     94% |196-205, 258-261 |
| coldfront/core/project/views\_/join\_views/approval\_views.py                                               |      217 |       42 |       64 |       17 |     76% |58-60, 75-\>81, 93-95, 104-106, 116-118, 128, 137-139, 149-152, 185-186, 204, 210, 242-247, 261-\>281, 265, 271, 276, 305-309, 312-313, 317-318, 340-341 |
| coldfront/core/project/views\_/join\_views/request\_views.py                                                |      169 |       54 |       48 |       15 |     64% |48-50, 62-86, 91, 98-103, 106-108, 113, 133-144, 166-169, 181-185, 192-197, 209-\>249, 214-220, 224, 233, 239, 243, 247 |
| coldfront/core/project/views\_/new\_project\_views/approval\_views.py                                       |      857 |      347 |      150 |       27 |     57% |93-\>95, 104-\>110, 186, 204-211, 223-227, 235, 305, 318-320, 354-359, 372-375, 386-391, 395-413, 427-442, 454-458, 462-465, 494-496, 515-516, 558-580, 611, 616-617, 654, 670-671, 725, 742-750, 804-808, 812, 838-840, 861-865, 868-873, 876-909, 912-914, 917-922, 925-930, 933, 946-950, 953-958, 961-980, 983-985, 988-991, 994, 1004-1009, 1012-1023, 1026-1049, 1067-1072, 1090, 1117-1129, 1135, 1161, 1167-1172, 1191-1196, 1200-1218, 1228-1265, 1282-1286, 1289-1294, 1297-1319, 1322-1324, 1327-1331, 1334, 1346-1350, 1353-1358, 1361-1394, 1397-1399, 1402-1406, 1409-1414, 1417, 1427-1432, 1435-1446, 1449-1463 |
| coldfront/core/project/views\_/new\_project\_views/request\_views.py                                        |      537 |      118 |      110 |       13 |     78% |67-74, 77-78, 92, 95-98, 181, 186-189, 287, 295, 300, 335-336, 341-344, 349-356, 417-420, 455, 467, 513-516, 545-548, 559-566, 590-592, 597-600, 612-615, 629, 646-\>654, 671-674, 687-706, 800-804, 898-911, 914-944, 947, 952-971 |
| coldfront/core/project/views\_/removal\_views.py                                                            |      265 |       38 |       76 |       15 |     82% |29-\>34, 56-58, 69, 141-148, 191-195, 211-216, 244-\>271, 248, 254, 260, 266, 295-299, 302-303, 307-308, 330-331, 363-365, 425-428 |
| coldfront/core/project/views\_/renewal\_views/approval\_views.py                                            |      327 |       24 |       64 |        4 |     93% |80-\>82, 91-\>100, 98, 131-134, 135-\>145, 141-144, 224-227, 237-244, 297-299, 314-315 |
| coldfront/core/project/views\_/renewal\_views/request\_views.py                                             |      562 |       49 |      142 |       23 |     90% |73, 76-79, 134, 162-\>171, 181-183, 186-192, 200-203, 219, 318, 327, 370, 373-378, 402-403, 412, 471, 475-479, 486-489, 531-\>544, 596-598, 642, 690-693, 765-\>774, 837-\>exit, 907-909, 965, 969-973, 976-979, 996-\>1005, 999-\>1005, 1008-\>1022, 1016 |
| coldfront/core/publication/admin.py                                                                         |       10 |       10 |        0 |        0 |      0% |      1-15 |
| coldfront/core/publication/apps.py                                                                          |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/publication/forms.py                                                                         |       30 |       30 |        0 |        0 |      0% |      1-43 |
| coldfront/core/publication/models.py                                                                        |       26 |       26 |        0 |        0 |      0% |      1-39 |
| coldfront/core/publication/urls.py                                                                          |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/publication/views.py                                                                         |      296 |      296 |       92 |        0 |      0% |     1-506 |
| coldfront/core/research\_output/admin.py                                                                    |       12 |       12 |        0 |        0 |      0% |      1-34 |
| coldfront/core/research\_output/apps.py                                                                     |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/research\_output/forms.py                                                                    |        6 |        6 |        0 |        0 |      0% |       1-9 |
| coldfront/core/research\_output/models.py                                                                   |       19 |       19 |        4 |        0 |      0% |      1-45 |
| coldfront/core/research\_output/urls.py                                                                     |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/research\_output/views.py                                                                    |       49 |       49 |        4 |        0 |      0% |      1-99 |
| coldfront/core/resource/admin.py                                                                            |       58 |       12 |        4 |        0 |     74% |30, 39-42, 59, 62-65, 75, 78, 90, 93 |
| coldfront/core/resource/apps.py                                                                             |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/management/commands/add\_resource\_defaults.py                                      |       11 |        0 |        6 |        0 |    100% |           |
| coldfront/core/resource/models.py                                                                           |      106 |       31 |       16 |        1 |     62% |14, 27, 32, 36, 51, 80-92, 96, 103, 106-108, 111, 126-141, 153 |
| coldfront/core/resource/utils.py                                                                            |       18 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/utils\_/allowance\_utils/computing\_allowance.py                                    |      130 |       17 |       58 |       12 |     78% |26-27, 34-\>36, 51-56, 71-\>73, 83-84, 94-95, 103-\>105, 118-121, 144-\>146, 162-\>168, 171, 181-\>184, 189-\>192 |
| coldfront/core/resource/utils\_/allowance\_utils/constants.py                                               |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/utils\_/allowance\_utils/interface.py                                               |       88 |        6 |       18 |        2 |     92% |66-\>56, 73-\>69, 99-100, 118-119, 126-127 |
| coldfront/core/resource/views.py                                                                            |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/core/socialaccount/adapter.py                                                                     |      163 |       22 |       42 |        8 |     85% |41-\>53, 44-48, 63, 95, 144-146, 257-264, 285-286, 325-329, 335-339, 347-351 |
| coldfront/core/socialaccount/apps.py                                                                        |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/socialaccount/signals.py                                                                     |       59 |       13 |       18 |        2 |     81% |35-40, 76-82, 94-100, 112-115 |
| coldfront/core/socialaccount/urls.py                                                                        |       16 |        0 |        8 |        0 |    100% |           |
| coldfront/core/statistics/admin.py                                                                          |       40 |        7 |        0 |        0 |     82% |26, 31, 42, 45, 48, 51, 54 |
| coldfront/core/statistics/apps.py                                                                           |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/statistics/forms.py                                                                          |       36 |       21 |       10 |        0 |     33% |    69-122 |
| coldfront/core/statistics/management/commands/free\_qos\_jobs.py                                            |      134 |      134 |       42 |        0 |      0% |     1-249 |
| coldfront/core/statistics/models.py                                                                         |       59 |        2 |        0 |        0 |     97% |    16, 69 |
| coldfront/core/statistics/urls.py                                                                           |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/statistics/utils\_/accounting\_utils.py                                                      |       72 |       19 |       20 |        0 |     77% |     34-67 |
| coldfront/core/statistics/utils\_/job\_accessibility\_manager.py                                            |       30 |       21 |       12 |        0 |     21% |12-14, 18-32, 38-51, 57-61 |
| coldfront/core/statistics/utils\_/job\_query\_filtering.py                                                  |       51 |       41 |       26 |        0 |     13% |9-43, 51-54, 57-62, 65, 69-75, 78-84 |
| coldfront/core/statistics/views.py                                                                          |      131 |       91 |       26 |        0 |     25% |40-87, 91-144, 156-166, 169-184, 198, 201-224, 230-248 |
| coldfront/core/user/\_\_init\_\_.py                                                                         |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/admin.py                                                                                |       33 |       10 |        6 |        0 |     59% |19, 22, 25, 33-39 |
| coldfront/core/user/apps.py                                                                                 |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/auth.py                                                                                 |       44 |       21 |        6 |        1 |     48% |24-46, 49-52 |
| coldfront/core/user/forms.py                                                                                |      150 |       71 |       22 |        0 |     46% |79-80, 83-96, 99-100, 103-104, 107-108, 111-119, 137-143, 149-150, 153-155, 167, 170, 173, 203-206, 209-212, 215-225, 241-245, 255-276, 286-290 |
| coldfront/core/user/forms\_/link\_login\_forms.py                                                           |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/management/commands/add\_default\_user\_choices.py                                      |        7 |        0 |        2 |        0 |    100% |           |
| coldfront/core/user/management/commands/create\_email\_addresses.py                                         |       25 |       25 |        4 |        0 |      0% |      1-53 |
| coldfront/core/user/management/commands/lower\_email\_case.py                                               |       34 |       34 |       10 |        0 |      0% |      1-53 |
| coldfront/core/user/management/commands/merge\_users.py                                                     |       56 |       56 |        6 |        0 |      0% |      1-94 |
| coldfront/core/user/management/commands/migrate\_email\_address\_model.py                                   |      111 |      111 |       48 |        0 |      0% |     1-235 |
| coldfront/core/user/management/commands/set\_passwords.py                                                   |       19 |       19 |        4 |        0 |      0% |      1-32 |
| coldfront/core/user/models.py                                                                               |       61 |       18 |        8 |        0 |     62% | 65-94, 97 |
| coldfront/core/user/signals.py                                                                              |       37 |        6 |       16 |        3 |     83% |31-32, 37-\>exit, 44, 46-48 |
| coldfront/core/user/urls.py                                                                                 |       27 |        0 |        2 |        1 |     97% |  98-\>106 |
| coldfront/core/user/utils.py                                                                                |      158 |      113 |       40 |        1 |     23% |29-30, 34, 37-51, 58-85, 91-95, 99-130, 141-177, 184, 201-211, 217-237, 243-264, 270-286 |
| coldfront/core/user/utils\_/host\_user\_utils.py                                                            |       29 |        1 |        6 |        1 |     94% |        59 |
| coldfront/core/user/utils\_/link\_login\_utils.py                                                           |       35 |        2 |        8 |        2 |     91% |    25, 48 |
| coldfront/core/user/utils\_/merge\_users/\_\_init\_\_.py                                                    |        2 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/utils\_/merge\_users/class\_handlers.py                                                 |      232 |      165 |       54 |        0 |     23% |25-26, 32-36, 46-59, 64-69, 75, 82-89, 96-97, 103-106, 111, 117-123, 127-129, 133-135, 142-143, 146, 155-158, 161-183, 186-212, 218, 221, 227, 230-231, 237-242, 245-258, 263-273, 279, 282-283, 289, 292-295, 301, 304-305, 311-316, 319-325, 332-340, 345-355, 361, 364-365, 371, 374-377, 383-390, 393-399, 405-411 |
| coldfront/core/user/utils\_/merge\_users/runner.py                                                          |       94 |       66 |       20 |        0 |     25% |32-43, 47, 51, 56-57, 63-75, 81, 89-105, 110-140, 150-151, 156, 161-163, 170-174 |
| coldfront/core/user/views.py                                                                                |      469 |      166 |      124 |       20 |     60% |51-\>56, 74-78, 109, 111-\>114, 132-144, 211-222, 225-232, 242-253, 257, 359-360, 426-427, 432-437, 448, 451, 454, 457, 461, 466, 472-476, 491-495, 498-499, 503-504, 509, 522-523, 533-541, 544, 551, 554-572, 581-585, 623-626, 629-634, 673-681, 691-714, 717, 724-725, 740-749, 760-767, 773-800, 806-808, 814-826 |
| coldfront/core/user/views\_/link\_login\_views.py                                                           |       69 |        5 |        6 |        0 |     93% |     88-95 |
| coldfront/core/user/views\_/request\_hub\_views.py                                                          |      337 |       11 |       48 |        6 |     95% |73-74, 149-150, 155-156, 201-206, 715-\>720, 720-\>723, 723-\>726 |
| coldfront/core/utils/admin.py                                                                               |       47 |       17 |       12 |        0 |     51% |36-46, 52-57 |
| coldfront/core/utils/apps.py                                                                                |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/common.py                                                                              |       81 |        8 |       18 |        0 |     90% |34-35, 39, 54, 60-65 |
| coldfront/core/utils/context\_processors.py                                                                 |       55 |        3 |       14 |        0 |     96% |     60-65 |
| coldfront/core/utils/email/\_\_init\_\_.py                                                                  |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/email/email\_strategy.py                                                               |       41 |        7 |        6 |        1 |     83% |18, 28-29, 50-51, 71-72 |
| coldfront/core/utils/flag\_conditions.py                                                                    |       14 |        1 |        2 |        1 |     88% |        14 |
| coldfront/core/utils/forms/file\_upload\_forms.py                                                           |       15 |        1 |        2 |        1 |     88% |        10 |
| coldfront/core/utils/mail.py                                                                                |       47 |       11 |       20 |        6 |     72% |13-\>21, 26, 33-34, 36-\>39, 40, 43, 59-60, 88-93 |
| coldfront/core/utils/management/commands/add\_accounting\_defaults.py                                       |       32 |        0 |        6 |        0 |    100% |           |
| coldfront/core/utils/management/commands/add\_allowance\_defaults.py                                        |       56 |        0 |       16 |        0 |    100% |           |
| coldfront/core/utils/management/commands/add\_scheduled\_tasks.py                                           |       12 |       12 |        0 |        0 |      0% |      1-21 |
| coldfront/core/utils/management/commands/audit\_data.py                                                     |      119 |      119 |       60 |        0 |      0% |    20-316 |
| coldfront/core/utils/management/commands/create\_existing\_brc\_data.py                                     |      448 |      448 |      136 |        0 |      0% |     1-893 |
| coldfront/core/utils/management/commands/create\_staff\_group.py                                            |       18 |        3 |        6 |        2 |     79% |14, 33-\>38, 42-43 |
| coldfront/core/utils/management/commands/export\_data.py                                                    |      352 |       49 |      128 |       17 |     83% |273-274, 291, 302-\>301, 324-373, 399, 408, 433-\>exit, 501-\>exit, 536-537, 539-\>exit, 571-\>565, 588-\>592, 595, 598, 623, 632-633, 635-\>exit, 665-666, 671-\>674, 677-678, 694-695, 700-701 |
| coldfront/core/utils/management/commands/import\_grants.py                                                  |       62 |       62 |       16 |        0 |      0% |     1-167 |
| coldfront/core/utils/management/commands/import\_projects.py                                                |       63 |       63 |       16 |        0 |      0% |     1-106 |
| coldfront/core/utils/management/commands/import\_publications.py                                            |       32 |       32 |        4 |        0 |      0% |      1-61 |
| coldfront/core/utils/management/commands/import\_resources.py                                               |       71 |       71 |       32 |        0 |      0% |     1-123 |
| coldfront/core/utils/management/commands/import\_resources\_from\_json.py                                   |       89 |       89 |       30 |        0 |      0% |     1-147 |
| coldfront/core/utils/management/commands/import\_subscriptions.py                                           |       89 |       89 |       24 |        0 |      0% |     1-165 |
| coldfront/core/utils/management/commands/import\_users.py                                                   |       30 |       30 |       12 |        0 |      0% |      1-50 |
| coldfront/core/utils/management/commands/initial\_setup.py                                                  |       13 |       13 |        0 |        0 |      0% |      1-22 |
| coldfront/core/utils/management/commands/list\_latest\_project\_transactions.py                             |       14 |       14 |        2 |        0 |      0% |      1-21 |
| coldfront/core/utils/management/commands/load\_brc\_allocation\_data.py                                     |      178 |      178 |       46 |        0 |      0% |     1-453 |
| coldfront/core/utils/management/commands/load\_brc\_project\_descriptions.py                                |       68 |       68 |       14 |        0 |      0% |     1-133 |
| coldfront/core/utils/management/commands/load\_lrc\_data.py                                                 |      547 |      547 |      156 |        0 |      0% |    1-1068 |
| coldfront/core/utils/management/commands/load\_nodes.py                                                     |       30 |       30 |        8 |        0 |      0% |      1-42 |
| coldfront/core/utils/management/commands/load\_project\_transactions.py                                     |       38 |       38 |        8 |        0 |      0% |      1-58 |
| coldfront/core/utils/management/commands/load\_project\_user\_transactions.py                               |       53 |       53 |       14 |        0 |      0% |      1-83 |
| coldfront/core/utils/management/commands/load\_test\_data.py                                                |      127 |      127 |       12 |        0 |      0% |     1-560 |
| coldfront/core/utils/management/commands/set\_allocation\_end\_dates\_for\_periodic\_projects.py            |       41 |       41 |        8 |        0 |      0% |      1-60 |
| coldfront/core/utils/management/commands/set\_allocation\_start\_dates.py                                   |       46 |       46 |        8 |        0 |      0% |      1-63 |
| coldfront/core/utils/management/commands/set\_service\_unit\_usages\_from\_jobs.py                          |       68 |       68 |       14 |        0 |      0% |     1-100 |
| coldfront/core/utils/management/commands/show\_users\_in\_project\_but\_not\_in\_allocation.py              |       17 |       17 |        6 |        0 |      0% |      1-29 |
| coldfront/core/utils/management/commands/transform\_jobs.py                                                 |       65 |       65 |       18 |        0 |      0% |      1-92 |
| coldfront/core/utils/management/commands/update\_state\_and\_extra\_fields.py                               |       53 |       53 |       30 |        0 |      0% |     16-90 |
| coldfront/core/utils/management/commands/utils.py                                                           |       19 |       19 |        2 |        0 |      0% |      1-60 |
| coldfront/core/utils/management/commands/validate\_lrc\_initial\_state.py                                   |      206 |      206 |       76 |        0 |      0% |     1-376 |
| coldfront/core/utils/middleware.py                                                                          |       14 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/mixins/views.py                                                                        |       67 |       26 |       18 |        2 |     55% |28-29, 45-49, 64-65, 80-90, 95-99, 104-111, 117-127 |
| coldfront/core/utils/models.py                                                                              |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/mou.py                                                                                 |       60 |        5 |       16 |        3 |     87% |22-\>25, 49-\>53, 74-81 |
| coldfront/core/utils/reporting/report\_message\_strategy.py                                                 |       51 |       51 |        2 |        0 |      0% |      1-84 |
| coldfront/core/utils/templatetags/common\_tags.py                                                           |       34 |       13 |       16 |        1 |     48% |38-41, 46-55, 63-\>exit |
| coldfront/core/utils/views/mou\_views.py                                                                    |      178 |       14 |       34 |        6 |     91% |63, 75, 138, 150, 201-202, 237, 239-\>243, 254-256, 287-292 |
| coldfront/plugins/departments/admin.py                                                                      |       32 |        8 |        4 |        0 |     67% |19, 30-33, 58, 61, 64 |
| coldfront/plugins/departments/apps.py                                                                       |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/conf/settings.py                                                              |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/forms.py                                                                      |       25 |        0 |        2 |        0 |    100% |           |
| coldfront/plugins/departments/management/commands/load\_departments.py                                      |       36 |       36 |       12 |        0 |      0% |      1-52 |
| coldfront/plugins/departments/management/commands/load\_user\_departments.py                                |       31 |       31 |        8 |        0 |      0% |      1-56 |
| coldfront/plugins/departments/models.py                                                                     |       17 |        1 |        0 |        0 |     94% |        24 |
| coldfront/plugins/departments/tasks.py                                                                      |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/urls.py                                                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/utils/\_\_init\_\_.py                                                         |       13 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/utils/data\_sources/\_\_init\_\_.py                                           |       13 |        2 |        0 |        0 |     85% |     22-23 |
| coldfront/plugins/departments/utils/data\_sources/backends/base.py                                          |        9 |        2 |        0 |        0 |     78% |    18, 41 |
| coldfront/plugins/departments/utils/data\_sources/backends/calnet\_ldap.py                                  |       79 |       79 |       32 |        0 |      0% |     1-244 |
| coldfront/plugins/departments/utils/data\_sources/backends/dummy.py                                         |       28 |        3 |       10 |        0 |     87% |     15-17 |
| coldfront/plugins/departments/utils/queries.py                                                              |       69 |        2 |       24 |        1 |     97% |     77-78 |
| coldfront/plugins/departments/views.py                                                                      |       36 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/admin.py                                                    |       16 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/api/permissions.py                                          |       15 |        1 |        8 |        1 |     91% |        27 |
| coldfront/plugins/faculty\_storage\_allocations/api/serializers.py                                          |       32 |        2 |        4 |        2 |     89% |    62, 87 |
| coldfront/plugins/faculty\_storage\_allocations/api/urls.py                                                 |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/api/views.py                                                |       42 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/apps.py                                                     |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/conf/settings.py                                            |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/\_\_init\_\_.py                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/approval\_forms.py                                    |       29 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/form\_utils.py                                        |       41 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/request\_forms.py                                     |       28 |        1 |        6 |        1 |     94% |        38 |
| coldfront/plugins/faculty\_storage\_allocations/management/commands/add\_faculty\_directory\_defaults.py    |       23 |        0 |        2 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/models.py                                                   |       57 |        1 |       10 |        0 |     99% |        40 |
| coldfront/plugins/faculty\_storage\_allocations/services/\_\_init\_\_.py                                    |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/directory\_service.py                              |      138 |        6 |       28 |        1 |     96% |62, 141-143, 221, 408-409 |
| coldfront/plugins/faculty\_storage\_allocations/services/eligibility\_service.py                            |       15 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/notification\_service.py                           |       50 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/request\_service.py                                |      134 |        8 |       22 |        6 |     91% |182-\>184, 194, 245-246, 283-287, 311-\>316, 318, 324 |
| coldfront/plugins/faculty\_storage\_allocations/signals.py                                                  |       38 |        0 |        8 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/urls.py                                                     |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/utils/\_\_init\_\_.py                                       |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/views/\_\_init\_\_.py                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/views/approval\_views.py                                    |      349 |       59 |       62 |       10 |     81% |59, 62-\>67, 132-\>139, 210-\>231, 213-229, 272-280, 293-360, 442, 445, 453-454, 463-466, 672-676, 766-769 |
| coldfront/plugins/faculty\_storage\_allocations/views/request\_views.py                                     |       85 |       18 |       12 |        3 |     78% |42, 57, 62-66, 78-79, 82-83, 86-88, 140-149 |
| coldfront/plugins/freeipa/\_\_init\_\_.py                                                                   |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/freeipa/apps.py                                                                           |        8 |        8 |        2 |        0 |      0% |      1-12 |
| coldfront/plugins/freeipa/management/commands/freeipa\_check.py                                             |      159 |      159 |       70 |        0 |      0% |     1-250 |
| coldfront/plugins/freeipa/management/commands/freeipa\_expire\_users.py                                     |       58 |       58 |       26 |        0 |      0% |      1-99 |
| coldfront/plugins/freeipa/search.py                                                                         |       46 |       46 |       10 |        0 |      0% |      1-73 |
| coldfront/plugins/freeipa/signals.py                                                                        |       18 |       18 |        0 |        0 |      0% |      1-29 |
| coldfront/plugins/freeipa/tasks.py                                                                          |       71 |       71 |       30 |        0 |      0% |     1-118 |
| coldfront/plugins/freeipa/utils.py                                                                          |       36 |       36 |        8 |        0 |      0% |      1-52 |
| coldfront/plugins/hardware\_procurements/conf/settings.py                                                   |        5 |        1 |        2 |        1 |     71% |         9 |
| coldfront/plugins/hardware\_procurements/forms.py                                                           |       18 |        5 |        0 |        0 |     72% |9, 49-50, 55-57 |
| coldfront/plugins/hardware\_procurements/management/commands/refresh\_hardware\_procurements\_cache.py      |       40 |       40 |        6 |        0 |      0% |      1-83 |
| coldfront/plugins/hardware\_procurements/urls.py                                                            |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/\_\_init\_\_.py                                              |       57 |        1 |        8 |        1 |     97% |        58 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/\_\_init\_\_.py                                |       11 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/base.py                               |        6 |        1 |        0 |        0 |     83% |        13 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/cached.py                             |       97 |        4 |       42 |        1 |     96% |134-\>exit, 178-179, 188-189 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/dummy.py                              |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/google\_sheets.py                     |       94 |        2 |       28 |        0 |     98% |     78-79 |
| coldfront/plugins/hardware\_procurements/views.py                                                           |      121 |       94 |       36 |        0 |     17% |26-28, 31-43, 48, 53-60, 63-65, 74-88, 98-99, 102-139, 142-143, 147-194 |
| coldfront/plugins/iquota/admin.py                                                                           |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/plugins/iquota/apps.py                                                                            |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/iquota/exceptions.py                                                                      |        7 |        7 |        0 |        0 |      0% |      1-15 |
| coldfront/plugins/iquota/urls.py                                                                            |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/iquota/utils.py                                                                           |       68 |       68 |       10 |        0 |      0% |     1-122 |
| coldfront/plugins/iquota/views.py                                                                           |       12 |       12 |        2 |        0 |      0% |      1-22 |
| coldfront/plugins/ldap\_user\_search/admin.py                                                               |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/plugins/ldap\_user\_search/apps.py                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/ldap\_user\_search/models.py                                                              |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/plugins/ldap\_user\_search/tests.py                                                               |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/ldap\_user\_search/utils.py                                                               |       37 |       37 |        6 |        0 |      0% |      1-58 |
| coldfront/plugins/ldap\_user\_search/views.py                                                               |        1 |        1 |        0 |        0 |      0% |         1 |
| coldfront/plugins/mokey\_oidc/apps.py                                                                       |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/mokey\_oidc/auth.py                                                                       |       67 |       67 |       26 |        0 |      0% |      1-94 |
| coldfront/plugins/slurm/\_\_init\_\_.py                                                                     |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/slurm/apps.py                                                                             |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/slurm/associations.py                                                                     |      168 |      168 |       74 |        0 |      0% |     1-248 |
| coldfront/plugins/slurm/management/commands/slurm\_check.py                                                 |      190 |      190 |       80 |        0 |      0% |     1-295 |
| coldfront/plugins/slurm/management/commands/slurm\_dump.py                                                  |       37 |       37 |       16 |        0 |      0% |      1-49 |
| coldfront/plugins/slurm/utils.py                                                                            |       79 |       79 |       18 |        0 |      0% |     1-100 |
| coldfront/plugins/system\_monitor/utils.py                                                                  |       94 |       94 |       10 |        0 |      0% |     1-148 |
| coldfront/plugins/xdmod/\_\_init\_\_.py                                                                     |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/xdmod/apps.py                                                                             |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/xdmod/management/commands/xdmod\_usage.py                                                 |      150 |      150 |       72 |        0 |      0% |     1-281 |
| coldfront/plugins/xdmod/utils.py                                                                            |       84 |       84 |       12 |        0 |      0% |     1-120 |
| **TOTAL**                                                                                                   | **26721** | **10925** | **6118** |  **592** | **56%** |           |

89 empty files skipped.


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/ucb-rit/coldfront/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/ucb-rit/coldfront/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ucb-rit/coldfront/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/ucb-rit/coldfront/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fucb-rit%2Fcoldfront%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/ucb-rit/coldfront/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.