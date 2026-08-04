# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/ucb-rit/coldfront/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                                        |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|------------------------------------------------------------------------------------------------------------ | -------: | -------: | -------: | -------: | ------: | --------: |
| coldfront/\_\_init\_\_.py                                                                                   |        8 |        3 |        0 |        0 |     62% |      9-12 |
| coldfront/api/allocation/filters.py                                                                         |       33 |        0 |        0 |        0 |    100% |           |
| coldfront/api/allocation/serializers.py                                                                     |       90 |        0 |       22 |        1 |     99% | 245-\>252 |
| coldfront/api/allocation/urls.py                                                                            |       18 |        0 |        0 |        0 |    100% |           |
| coldfront/api/allocation/views.py                                                                           |       90 |        0 |       12 |        4 |     96% |65-\>69, 97-\>101, 128-\>132, 146-\>150 |
| coldfront/api/billing/serializers.py                                                                        |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/api/billing/urls.py                                                                               |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/api/billing/views.py                                                                              |       13 |        0 |        0 |        0 |    100% |           |
| coldfront/api/permissions.py                                                                                |       28 |        1 |       12 |        1 |     95% |        57 |
| coldfront/api/project/filters.py                                                                            |       43 |        3 |        8 |        2 |     90% |50-\>47, 52-53, 59 |
| coldfront/api/project/serializers.py                                                                        |       36 |        0 |        4 |        0 |    100% |           |
| coldfront/api/project/urls.py                                                                               |       11 |        0 |        0 |        0 |    100% |           |
| coldfront/api/project/views.py                                                                              |       49 |        1 |        4 |        1 |     96% |       109 |
| coldfront/api/resource/serializers.py                                                                       |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/api/statistics/pagination.py                                                                      |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/api/statistics/serializers.py                                                                     |      136 |       18 |       34 |        7 |     84% |29-30, 86, 89-90, 106-109, 161-164, 177-179, 213-\>230, 215-220, 236-\>248, 238-242 |
| coldfront/api/statistics/urls.py                                                                            |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/api/statistics/utils.py                                                                           |      156 |       27 |       46 |       19 |     77% |66, 68, 94, 96, 146, 148, 150, 208, 242, 300, 302, 305-308, 331, 333, 336-339, 366, 368, 370, 400, 402, 404 |
| coldfront/api/statistics/views.py                                                                           |      298 |       19 |       54 |        5 |     93% |168, 175-176, 192-193, 199-\>206, 202-203, 227-228, 324-330, 339-345, 491, 698-701, 712-714 |
| coldfront/api/urls.py                                                                                       |        7 |        0 |        2 |        1 |     89% | 18-\>exit |
| coldfront/api/user/authentication.py                                                                        |       19 |        2 |        4 |        2 |     83% |    20, 23 |
| coldfront/api/user/filters.py                                                                               |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/api/user/serializers.py                                                                           |       38 |        0 |        2 |        0 |    100% |           |
| coldfront/api/user/urls.py                                                                                  |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/api/user/views.py                                                                                 |       97 |       25 |       24 |        1 |     74% |49-75, 217-\>233 |
| coldfront/api/utils/urls.py                                                                                 |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/core/account/adapter.py                                                                           |       10 |        5 |        4 |        0 |     36% |     13-17 |
| coldfront/core/account/admin.py                                                                             |       44 |        5 |       12 |        0 |     91% |     54-62 |
| coldfront/core/account/apps.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/account/urls.py                                                                              |       13 |        0 |        8 |        0 |    100% |           |
| coldfront/core/account/utils/login\_activity.py                                                             |       44 |        3 |        4 |        2 |     90% | 60-61, 77 |
| coldfront/core/account/utils/queries.py                                                                     |       34 |        8 |        8 |        0 |     81% |     25-32 |
| coldfront/core/allocation/admin.py                                                                          |      262 |       93 |       44 |        0 |     55% |143, 146, 149, 152-155, 158-162, 165-169, 172-178, 202, 212-222, 271-274, 277, 280, 283-284, 292, 295, 298-301, 304-308, 311-315, 367, 370, 373, 376-377, 380, 383-386, 389-393, 396-400, 403, 406, 410, 431, 440-450, 478, 481, 484-485, 546, 549, 552-553, 561, 564, 567, 570-573, 576-580, 608, 611, 614, 638 |
| coldfront/core/allocation/apps.py                                                                           |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/forms.py                                                                          |      169 |       36 |       24 |        5 |     72% |49-87, 109-114, 154-155, 240-241, 301-302, 311-312, 324, 330-\>334, 349-356, 368 |
| coldfront/core/allocation/forms\_/secure\_dir\_forms.py                                                     |       76 |        3 |       10 |        4 |     92% |22-\>26, 30, 96, 210 |
| coldfront/core/allocation/management/commands/add\_allocation\_defaults.py                                  |       26 |        0 |       16 |        0 |    100% |           |
| coldfront/core/allocation/management/commands/add\_directory\_defaults.py                                   |       31 |        0 |        4 |        0 |    100% |           |
| coldfront/core/allocation/management/commands/approve\_renewal\_requests\_for\_allocation\_period.py        |       74 |        4 |       14 |        1 |     94% |109, 133-139 |
| coldfront/core/allocation/management/commands/audit\_allocation\_period.py                                  |      169 |      123 |       34 |        0 |     23% |34-39, 50-90, 99-118, 138-140, 148-150, 153-155, 159-161, 164-178, 183-192, 198-221, 226, 229-231, 234-244, 249, 257, 260-264, 269-285, 288, 296-301, 308-322, 325-327, 330-335 |
| coldfront/core/allocation/management/commands/convert\_cluster\_attributes\_to\_cluster\_access\_request.py |       61 |       61 |       26 |        0 |      0% |     1-179 |
| coldfront/core/allocation/management/commands/correct\_user\_service\_units.py                              |       65 |       65 |       12 |        0 |      0% |     1-139 |
| coldfront/core/allocation/management/commands/create\_allocation\_periods.py                                |       71 |       20 |       22 |        4 |     70% |45-46, 51-76, 87, 90, 106-\>114 |
| coldfront/core/allocation/management/commands/load\_allocation\_renewal\_requests.py                        |      200 |      200 |       38 |        0 |      0% |     1-423 |
| coldfront/core/allocation/management/commands/parse\_academic\_calendar.py                                  |       60 |       60 |       18 |        0 |      0% |     1-161 |
| coldfront/core/allocation/management/commands/schedule\_allocation\_period\_audits.py                       |      104 |      104 |       20 |        0 |      0% |     1-246 |
| coldfront/core/allocation/management/commands/send\_allowance\_renewal\_available\_emails.py                |       39 |       39 |        8 |        0 |      0% |      1-85 |
| coldfront/core/allocation/management/commands/set\_allocation\_renewal\_request\_computing\_allowances.py   |       30 |       30 |        4 |        0 |      0% |      1-56 |
| coldfront/core/allocation/management/commands/start\_allocation\_period.py                                  |      168 |       21 |       40 |        3 |     88% |173, 295-\>308, 316-323, 329-336, 342-349, 361-364, 386 |
| coldfront/core/allocation/models.py                                                                         |      436 |       85 |       92 |        8 |     75% |82-100, 117, 126, 142-161, 164, 179, 182-187, 190-207, 210-213, 225, 235, 244, 264, 293-304, 337, 358, 370, 400-410, 440-458, 594, 671-673, 681, 713, 739, 764, 806, 812, 841, 864 |
| coldfront/core/allocation/signals.py                                                                        |       21 |        1 |        8 |        1 |     93% |        45 |
| coldfront/core/allocation/signals\_/renewal\_signals.py                                                     |       24 |        0 |        2 |        0 |    100% |           |
| coldfront/core/allocation/tasks.py                                                                          |       67 |       67 |       28 |        0 |      0% |     1-210 |
| coldfront/core/allocation/urls.py                                                                           |       13 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils.py                                                                          |      119 |       31 |       36 |        5 |     70% |32-35, 40-62, 67-75, 80-93, 209, 211, 213, 215, 277 |
| coldfront/core/allocation/utils\_/accounting\_utils/\_\_init\_\_.py                                         |      130 |        2 |       30 |        9 |     93% |118-\>121, 164-\>exit, 216-217, 227-\>234, 278-\>exit, 289-\>exit, 392-\>394, 398-\>405, 447-\>449, 459-\>466 |
| coldfront/core/allocation/utils\_/accounting\_utils/domain.py                                               |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils\_/accounting\_utils/services/\_\_init\_\_.py                                |        2 |        0 |        0 |        0 |    100% |           |
| coldfront/core/allocation/utils\_/accounting\_utils/services/service\_units\_usage\_service.py              |       59 |        2 |       12 |        0 |     97% |     54-55 |
| coldfront/core/allocation/utils\_/cluster\_access\_utils.py                                                 |      203 |       12 |       18 |        5 |     92% |116-117, 139-144, 179, 241-242, 326, 369-370, 417-\>exit, 444-\>exit, 473 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/\_\_init\_\_.py                                        |       53 |        4 |       20 |        1 |     90% |27, 146-150 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/new\_directory.py                                      |      305 |       47 |       56 |       20 |     80% |65, 67, 69, 79, 110, 158, 259-264, 290-297, 315, 339-\>342, 357-363, 394-402, 415-421, 450, 478-\>481, 496-502, 557, 570-572, 581, 585, 593, 636-638, 645-647, 654-655, 664, 703, 705 |
| coldfront/core/allocation/utils\_/secure\_dir\_utils/user\_management.py                                    |      102 |        7 |        8 |        3 |     91% |42, 44, 112, 129-134, 226 |
| coldfront/core/allocation/views.py                                                                          |      953 |      670 |      328 |       31 |     25% |78-\>87, 92, 111, 124-142, 149-157, 182-208, 211, 214, 224, 233, 243, 282-406, 416-424, 426-435, 448, 460-489, 502-547, 587-594, 600-605, 618, 644, 650, 660, 666, 674, 689, 695-696, 703-706, 734-738, 741-742, 746-747, 754, 767-768, 781-793, 798-820, 823-866, 870-872, 877-975, 978, 986-991, 996-1023, 1026-1054, 1057-1069, 1072-1117, 1125-1130, 1135-1159, 1162-1186, 1189-1203, 1206-1247, 1261-1264, 1269-1273, 1276-1280, 1284-1286, 1289, 1299-1302, 1309-1321, 1324-1342, 1345-1382, 1391-1394, 1399-1409, 1416-1419, 1424-1478, 1485-1488, 1493-1535, 1543-1556, 1559-1596, 1599-1618, 1621-1644, 1647-1756, 1768-1775, 1779-1787, 1799-1803, 1806-1819, 1822-1838, 1853-1857, 1860-1864, 1869-1876, 1879, 1896-1900, 1903, 1915-1919, 1923-1932, 1935-1946, 1950-1971, 1984-1994, 1997-2001, 2004-2012, 2015, 2026-2036, 2039 |
| coldfront/core/allocation/views\_/cluster\_access\_views.py                                                 |      279 |       91 |       68 |       22 |     62% |42-43, 47-63, 66-109, 112-135, 149-154, 169-\>194, 173, 178, 183, 190, 204-205, 217-221, 224-225, 229-230, 252-253, 258-259, 279-280, 289-291, 325-327, 350-351, 360-362, 401-\>405, 403, 408-410, 413-\>415, 432, 447-448, 457-459, 493-\>497, 495 |
| coldfront/core/allocation/views\_/secure\_dir\_views/new\_directory/approval\_views.py                      |      446 |       41 |       82 |       18 |     88% |58-63, 102, 107-112, 119, 183-186, 195-203, 316-318, 321-323, 328-333, 345-346, 352, 394, 463, 540, 561-\>563, 614, 636, 680, 688-\>693, 694-\>699, 700-\>705, 706-\>710, 768-770 |
| coldfront/core/allocation/views\_/secure\_dir\_views/new\_directory/request\_views.py                       |      138 |       19 |       14 |        2 |     86% |62-66, 72-77, 92-93, 96-97, 100-102, 182-185, 279-280 |
| coldfront/core/allocation/views\_/secure\_dir\_views/user\_management/approval\_views.py                    |      271 |       32 |       72 |       16 |     84% |61-66, 87-\>110, 91, 96, 101, 106, 123-127, 130-131, 135-136, 143, 161-162, 189, 278, 338-341, 377, 424-\>427, 490-493, 506, 553-\>556 |
| coldfront/core/allocation/views\_/secure\_dir\_views/user\_management/request\_views.py                     |      112 |       11 |       20 |        3 |     88% |54-56, 111-114, 124-125, 143-\>141, 185-186 |
| coldfront/core/billing/admin.py                                                                             |       12 |        1 |        0 |        0 |     92% |        15 |
| coldfront/core/billing/forms.py                                                                             |       80 |       22 |       10 |        1 |     68% |18, 29-\>exit, 81-82, 100-105, 110-117, 131-136 |
| coldfront/core/billing/management/commands/billing\_ids.py                                                  |      230 |       56 |       52 |        1 |     72% |143-144, 152-153, 164-165, 184-186, 197-258, 277-\>exit, 345-347 |
| coldfront/core/billing/models.py                                                                            |       20 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/urls.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/\_\_init\_\_.py                                                                |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/billing\_activity\_managers.py                                                 |      125 |        9 |       10 |        0 |     93% |65, 71, 76, 82, 105, 111, 130, 175, 215 |
| coldfront/core/billing/utils/queries.py                                                                     |      127 |       40 |       36 |        4 |     63% |65, 71-\>76, 117-\>121, 173-234, 265 |
| coldfront/core/billing/utils/validation/\_\_init\_\_.py                                                     |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/validation/backends/base.py                                                    |        5 |        1 |        0 |        0 |     80% |        11 |
| coldfront/core/billing/utils/validation/backends/dummy.py                                                   |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/utils/validation/backends/oracle.py                                                  |       14 |       14 |        0 |        0 |      0% |      1-26 |
| coldfront/core/billing/utils/validation/backends/permissive.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/billing/views/admin\_views.py                                                                |      213 |      168 |       56 |        0 |     17% |43, 46-72, 75, 88-92, 95, 98-103, 106-145, 148-152, 155-160, 163-174, 177-179, 193-212, 221-222, 225-325, 333, 336-359, 362 |
| coldfront/core/field\_of\_science/\_\_init\_\_.py                                                           |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/admin.py                                                                  |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/apps.py                                                                   |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/core/field\_of\_science/management/commands/import\_field\_of\_science\_data.py                   |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/core/field\_of\_science/models.py                                                                 |       14 |        0 |        0 |        0 |    100% |           |
| coldfront/core/grant/admin.py                                                                               |       19 |       19 |        2 |        0 |      0% |      1-63 |
| coldfront/core/grant/apps.py                                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/grant/forms.py                                                                               |       16 |       16 |        0 |        0 |      0% |      1-30 |
| coldfront/core/grant/models.py                                                                              |       42 |       42 |        2 |        0 |      0% |      1-79 |
| coldfront/core/grant/urls.py                                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/grant/views.py                                                                               |      133 |      133 |       40 |        0 |      0% |     1-293 |
| coldfront/core/portal/admin.py                                                                              |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/portal/apps.py                                                                               |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/portal/templatetags/portal\_tags.py                                                          |        9 |        1 |        0 |        0 |     89% |        14 |
| coldfront/core/portal/utils.py                                                                              |       37 |       31 |        4 |        0 |     15% |8-24, 29-31, 36-66, 71-104 |
| coldfront/core/portal/views.py                                                                              |       91 |       41 |       14 |        2 |     57% |83-84, 154, 159-161, 167-229, 235-266, 272-295 |
| coldfront/core/project/\_\_init\_\_.py                                                                      |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/admin.py                                                                             |      113 |       32 |       16 |        0 |     63% |87, 90, 93-96, 99-103, 106-110, 188-189, 197-200, 203-207, 210-214, 217-223, 239-240, 248, 256 |
| coldfront/core/project/apps.py                                                                              |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/forms.py                                                                             |      130 |       18 |       12 |        2 |     85% |66-67, 77-108, 138-161, 279, 299-\>exit |
| coldfront/core/project/forms\_/new\_project\_forms/approval\_forms.py                                       |       68 |       41 |       18 |        1 |     33% |29-\>exit, 81-85, 88-97, 100-116, 166-169, 172-181, 184-198 |
| coldfront/core/project/forms\_/new\_project\_forms/request\_forms.py                                        |      304 |       25 |       90 |       16 |     88% |85, 88, 102, 114-\>116, 125, 145-\>147, 274, 311, 316-317, 354-356, 568, 619-\>629, 640-644, 688-\>exit, 698, 705, 998-1003 |
| coldfront/core/project/forms\_/removal\_forms.py                                                            |       21 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/forms\_/renewal\_forms/approval\_forms.py                                            |       14 |        0 |        2 |        1 |     94% | 27-\>exit |
| coldfront/core/project/forms\_/renewal\_forms/request\_forms.py                                             |      145 |       13 |       28 |        5 |     87% |84-\>115, 185, 191, 254-262, 277-278, 285-286, 639-647 |
| coldfront/core/project/management/commands/add\_default\_project\_choices.py                                |       18 |        0 |       12 |        0 |    100% |           |
| coldfront/core/project/management/commands/add\_service\_units\_to\_project.py                              |       62 |        0 |        8 |        0 |    100% |           |
| coldfront/core/project/management/commands/compute\_preemptive\_su\_deduction.py                            |      126 |       13 |       28 |        5 |     86% |222-230, 278-\>276, 285-293, 318-327, 329-337 |
| coldfront/core/project/management/commands/deactivate\_ica\_projects.py                                     |       59 |        3 |       10 |        0 |     96% |   117-119 |
| coldfront/core/project/management/commands/pending\_join\_request\_reminder.py                              |       55 |        6 |       12 |        2 |     88% |47-\>36, 93-95, 107-\>97, 139-141 |
| coldfront/core/project/management/commands/projects.py                                                      |      208 |       72 |       36 |        3 |     61% |74, 75-\>exit, 164-219, 223-249, 350-352, 368-428, 484-485, 532 |
| coldfront/core/project/management/commands/remove\_project\_users.py                                        |       69 |        0 |       18 |        0 |    100% |           |
| coldfront/core/project/management/commands/set\_new\_project\_request\_allocation\_periods.py               |       84 |       84 |       26 |        0 |      0% |     1-193 |
| coldfront/core/project/management/commands/set\_new\_project\_request\_computing\_allowances.py             |       30 |       30 |        4 |        0 |      0% |      1-56 |
| coldfront/core/project/management/commands/set\_new\_project\_request\_times.py                             |       17 |       17 |        6 |        0 |      0% |      1-54 |
| coldfront/core/project/models.py                                                                            |      279 |       40 |       42 |        7 |     83% |60, 68, 87-96, 113, 125, 135, 251, 260, 267, 300, 349-350, 364, 517, 532-541, 568, 600-617, 634 |
| coldfront/core/project/signals.py                                                                           |       37 |       15 |        0 |        0 |     59% |32-35, 41-49, 63-72 |
| coldfront/core/project/templatetags/iso8601\_to\_datetime.py                                                |       10 |        0 |        2 |        0 |    100% |           |
| coldfront/core/project/urls.py                                                                              |       35 |        0 |        2 |        1 |     97% | 451-\>471 |
| coldfront/core/project/utils.py                                                                             |      108 |       12 |       20 |        7 |     85% |62, 79-\>84, 96, 131, 148-\>153, 164, 208-\>211, 248-255 |
| coldfront/core/project/utils\_/addition\_utils.py                                                           |      110 |        7 |        6 |        1 |     93% |54, 59, 175-177, 224-225 |
| coldfront/core/project/utils\_/email\_utils.py                                                              |        6 |        1 |        2 |        1 |     75% |        22 |
| coldfront/core/project/utils\_/new\_project\_user\_utils.py                                                 |      203 |       11 |       54 |        2 |     95% |77-79, 201, 224-229, 246-251, 441 |
| coldfront/core/project/utils\_/new\_project\_utils.py                                                       |      360 |       76 |       82 |       25 |     73% |82-\>85, 85-\>87, 111-\>115, 135-\>140, 168-170, 190, 230-231, 268, 280, 317-318, 346-\>348, 363-365, 386-392, 403, 417, 448, 451-452, 466-469, 499, 502-503, 517-520, 556, 588, 591-592, 618-645, 653, 656-659, 691, 694-695, 730, 736-755, 764, 771, 780 |
| coldfront/core/project/utils\_/permissions\_utils.py                                                        |        8 |        2 |        4 |        2 |     67% |    10, 12 |
| coldfront/core/project/utils\_/removal\_utils.py                                                            |      176 |        6 |       28 |        3 |     96% |127-\>exit, 228-229, 305, 351-\>365, 403-408 |
| coldfront/core/project/utils\_/renewal\_survey/\_\_init\_\_.py                                              |       16 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/utils\_/renewal\_survey/backends/base.py                                             |       11 |        3 |        0 |        0 |     73% |26, 48, 71 |
| coldfront/core/project/utils\_/renewal\_survey/backends/google\_forms.py                                    |      110 |       76 |       46 |        0 |     27% |30-55, 62-97, 109-147, 219-235 |
| coldfront/core/project/utils\_/renewal\_survey/backends/permissive.py                                       |        8 |        0 |        0 |        0 |    100% |           |
| coldfront/core/project/utils\_/renewal\_utils.py                                                            |      539 |      125 |      100 |       24 |     74% |120, 171-180, 193-212, 222, 229, 231, 278-\>283, 283-\>285, 304-337, 354, 382, 413, 439, 476-510, 519, 552, 571-574, 590, 619, 634-636, 662, 685-713, 721-739, 744-752, 758-764, 777-786, 800, 806, 814, 836-838, 854-\>exit, 860, 864, 869, 875, 880, 885, 921, 925, 930, 936, 941, 946, 955-956, 1102-1106, 1110-1117, 1127-1128, 1147, 1165-1166 |
| coldfront/core/project/utils\_/request\_processing\_utils.py                                                |       55 |        0 |       26 |        0 |    100% |           |
| coldfront/core/project/views.py                                                                             |      765 |      426 |      252 |       29 |     40% |97-\>106, 167, 258, 282-285, 309-\>315, 380-389, 412-417, 469-475, 479, 489, 497, 501, 505-528, 552-553, 558-559, 563-564, 585-586, 626-627, 631-731, 735-784, 792-796, 807-814, 817-828, 842-843, 849-861, 864, 880, 884-\>exit, 897-898, 916-926, 942, 945-948, 959-969, 985, 988-1061, 1072-1079, 1106-1197, 1224-1257, 1284, 1295-1307, 1316-1323, 1331-1354, 1362-1372, 1375-1414, 1417-1535, 1548-1565, 1573-1585, 1590-1619, 1622-1637, 1640-1680, 1700, 1705, 1716, 1721, 1752, 1757, 1772-\>1774, 1777-1804, 1807 |
| coldfront/core/project/views\_/addition\_views/approval\_views.py                                           |      281 |       29 |       36 |        3 |     89% |124-127, 136-144, 225-227, 247-249, 304-309, 377, 390, 421-423, 521-\>527, 539-541 |
| coldfront/core/project/views\_/addition\_views/request\_views.py                                            |      144 |       10 |       18 |        0 |     94% |205-215, 269-272 |
| coldfront/core/project/views\_/join\_views/approval\_views.py                                               |      209 |       42 |       64 |       17 |     75% |67-69, 85-\>90, 102-104, 111-113, 123-125, 136, 145-147, 158-161, 195-196, 214, 221, 253-258, 272-\>290, 276, 281, 286, 313-317, 320-321, 325-326, 347-348 |
| coldfront/core/project/views\_/join\_views/request\_views.py                                                |      155 |       54 |       48 |       15 |     61% |45-49, 61-90, 95, 104-110, 113-117, 122, 142-153, 174-177, 188-192, 199-204, 221-\>266, 226-232, 236, 246, 254, 258, 262 |
| coldfront/core/project/views\_/new\_project\_views/approval\_views.py                                       |      835 |      347 |      150 |       27 |     56% |107-\>109, 119-\>125, 203, 220-227, 245-250, 257, 337, 351-353, 390-397, 410-413, 423-427, 431-450, 464-482, 494-498, 503-506, 539-541, 563-564, 610-633, 671, 675-676, 714, 730-731, 787, 804-811, 865-870, 875, 902-904, 926-930, 933-938, 941-975, 978-980, 983-989, 992-997, 1000, 1013-1017, 1020-1025, 1028-1048, 1051-1053, 1056-1059, 1062, 1072-1076, 1079-1093, 1096-1120, 1138-1143, 1161, 1185-1197, 1203, 1232, 1238-1245, 1263-1267, 1271-1290, 1299-1339, 1357-1361, 1364-1369, 1372-1395, 1398-1400, 1403-1407, 1410, 1423-1427, 1430-1435, 1438-1472, 1475-1477, 1480-1485, 1488-1493, 1496, 1506-1510, 1513-1527, 1530-1545 |
| coldfront/core/project/views\_/new\_project\_views/request\_views.py                                        |      513 |      118 |      110 |       13 |     77% |72-80, 83-84, 99, 102-106, 189, 193-197, 295, 305, 309, 347-348, 353-355, 360-366, 427-430, 466, 480, 527-530, 559-562, 575-582, 607-609, 614-616, 626-628, 642, 660-\>667, 685-687, 700-720, 821-825, 927-940, 943-972, 975, 980-999 |
| coldfront/core/project/views\_/removal\_views.py                                                            |      264 |       38 |       76 |       15 |     82% |33-\>38, 65-66, 79, 154-160, 203-206, 220-225, 259-\>282, 263, 268, 273, 278, 305-309, 312-313, 317-318, 340-341, 373-375, 437-439 |
| coldfront/core/project/views\_/renewal\_views/approval\_views.py                                            |      312 |       24 |       64 |        4 |     93% |86-\>88, 98-\>108, 105, 140-143, 144-\>155, 151-154, 236-239, 250-258, 315-317, 332-333 |
| coldfront/core/project/views\_/renewal\_views/request\_views.py                                             |      538 |       49 |      142 |       23 |     89% |93, 96-100, 152, 181-\>190, 199-201, 204-208, 219-221, 237, 345, 354, 398, 402-407, 435-436, 445, 506, 509-514, 522-525, 571-\>584, 640-642, 685, 733-735, 815-\>823, 891-\>exit, 964-966, 1021, 1024-1029, 1032-1035, 1053-\>1061, 1055-\>1061, 1064-\>1078, 1072 |
| coldfront/core/publication/admin.py                                                                         |       10 |       10 |        0 |        0 |      0% |      1-18 |
| coldfront/core/publication/apps.py                                                                          |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/publication/forms.py                                                                         |       29 |       29 |        0 |        0 |      0% |      1-42 |
| coldfront/core/publication/models.py                                                                        |       26 |       26 |        0 |        0 |      0% |      1-38 |
| coldfront/core/publication/urls.py                                                                          |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/publication/views.py                                                                         |      292 |      292 |       92 |        0 |      0% |     1-566 |
| coldfront/core/research\_output/admin.py                                                                    |       12 |       12 |        0 |        0 |      0% |      1-33 |
| coldfront/core/research\_output/apps.py                                                                     |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/research\_output/forms.py                                                                    |        6 |        6 |        0 |        0 |      0% |       1-9 |
| coldfront/core/research\_output/models.py                                                                   |       19 |       19 |        4 |        0 |      0% |      1-45 |
| coldfront/core/research\_output/urls.py                                                                     |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/core/research\_output/views.py                                                                    |       49 |       49 |        4 |        0 |      0% |     1-103 |
| coldfront/core/resource/admin.py                                                                            |       58 |       12 |        4 |        0 |     74% |64, 76-79, 128, 131-134, 151, 154, 173, 176 |
| coldfront/core/resource/apps.py                                                                             |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/management/commands/add\_resource\_defaults.py                                      |       11 |        0 |        6 |        0 |    100% |           |
| coldfront/core/resource/models.py                                                                           |      106 |       34 |       16 |        0 |     59% |14, 29, 35, 40, 57, 89-105, 109, 114-119, 122-125, 128, 145-171, 184 |
| coldfront/core/resource/utils.py                                                                            |       15 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/utils\_/allowance\_utils/computing\_allowance.py                                    |      129 |       17 |       58 |       12 |     78% |27-28, 35-\>37, 52-57, 72-\>74, 84-85, 95-96, 104-\>106, 119-122, 145-\>147, 163-\>170, 173, 183-\>186, 191-\>194 |
| coldfront/core/resource/utils\_/allowance\_utils/constants.py                                               |       10 |        0 |        0 |        0 |    100% |           |
| coldfront/core/resource/utils\_/allowance\_utils/interface.py                                               |       85 |        6 |       18 |        2 |     92% |70-\>60, 77-\>74, 104-105, 123-124, 131-132 |
| coldfront/core/socialaccount/adapter.py                                                                     |      162 |       22 |       42 |        8 |     85% |42-\>55, 45-50, 65, 97, 153-155, 275-283, 304-305, 345-350, 356-361, 370-375 |
| coldfront/core/socialaccount/apps.py                                                                        |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/socialaccount/signals.py                                                                     |       57 |       13 |       18 |        2 |     80% |31-37, 72-79, 92-99, 110-112 |
| coldfront/core/socialaccount/urls.py                                                                        |       16 |        0 |        8 |        0 |    100% |           |
| coldfront/core/statistics/admin.py                                                                          |       36 |        7 |        0 |        0 |     81% |37, 43, 61, 64, 67, 70, 73 |
| coldfront/core/statistics/apps.py                                                                           |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/statistics/forms.py                                                                          |       36 |       21 |       10 |        0 |     33% |    61-115 |
| coldfront/core/statistics/management/commands/free\_qos\_jobs.py                                            |      132 |      132 |       42 |        0 |      0% |     1-261 |
| coldfront/core/statistics/models.py                                                                         |       57 |        2 |        0 |        0 |     96% |    15, 67 |
| coldfront/core/statistics/urls.py                                                                           |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/statistics/utils\_/accounting\_utils.py                                                      |       69 |       19 |       20 |        0 |     76% |     37-73 |
| coldfront/core/statistics/utils\_/job\_accessibility\_manager.py                                            |       30 |       21 |       12 |        0 |     21% |12-13, 17-32, 38-52, 59-63 |
| coldfront/core/statistics/utils\_/job\_query\_filtering.py                                                  |       51 |       41 |       26 |        0 |     13% |8-37, 45-48, 51-56, 59, 62-69, 72-79 |
| coldfront/core/statistics/views.py                                                                          |      130 |       91 |       26 |        0 |     25% |47-93, 96-151, 161-172, 175-191, 202, 205-230, 236-271 |
| coldfront/core/user/\_\_init\_\_.py                                                                         |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/admin.py                                                                                |       31 |       10 |        6 |        0 |     57% |20, 23, 26, 33-39 |
| coldfront/core/user/apps.py                                                                                 |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/auth.py                                                                                 |       43 |       21 |        6 |        1 |     47% |24-47, 50-53 |
| coldfront/core/user/forms.py                                                                                |      148 |       71 |       22 |        0 |     45% |103-104, 107-123, 126-127, 130-131, 134-135, 138-146, 169-176, 183-184, 187-189, 203, 206, 209, 242-245, 248-251, 254-266, 281-286, 302-323, 343-347 |
| coldfront/core/user/forms\_/link\_login\_forms.py                                                           |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/management/commands/add\_default\_user\_choices.py                                      |        7 |        0 |        2 |        0 |    100% |           |
| coldfront/core/user/management/commands/create\_email\_addresses.py                                         |       25 |       25 |        4 |        0 |      0% |      1-51 |
| coldfront/core/user/management/commands/lower\_email\_case.py                                               |       34 |       34 |       10 |        0 |      0% |      1-51 |
| coldfront/core/user/management/commands/merge\_users.py                                                     |       55 |       55 |        6 |        0 |      0% |     1-101 |
| coldfront/core/user/management/commands/migrate\_email\_address\_model.py                                   |      111 |      111 |       48 |        0 |      0% |     1-243 |
| coldfront/core/user/management/commands/set\_passwords.py                                                   |       19 |       19 |        4 |        0 |      0% |      1-33 |
| coldfront/core/user/models.py                                                                               |       59 |       18 |        8 |        0 |     61% |66-97, 100 |
| coldfront/core/user/signals.py                                                                              |       36 |        6 |       16 |        3 |     83% |36-37, 44-\>exit, 58, 63-65 |
| coldfront/core/user/urls.py                                                                                 |       21 |        0 |        2 |        1 |     96% | 130-\>140 |
| coldfront/core/user/utils.py                                                                                |      156 |      113 |       40 |        1 |     22% |24-25, 29, 32-46, 53-86, 91-97, 101-138, 149-185, 192, 209-219, 225-247, 253-273, 278-296 |
| coldfront/core/user/utils\_/host\_user\_utils.py                                                            |       29 |        1 |        6 |        1 |     94% |        57 |
| coldfront/core/user/utils\_/link\_login\_utils.py                                                           |       34 |        2 |        8 |        2 |     90% |    23, 47 |
| coldfront/core/user/utils\_/merge\_users/\_\_init\_\_.py                                                    |        2 |        0 |        0 |        0 |    100% |           |
| coldfront/core/user/utils\_/merge\_users/class\_handlers.py                                                 |      229 |      165 |       54 |        0 |     23% |20-21, 27-31, 41-54, 59-64, 70, 77-83, 93-94, 100-101, 106, 112-118, 122-124, 128-130, 135-136, 139, 148-151, 154-178, 181-209, 214, 217, 222, 225-226, 231-237, 240-253, 258-271, 276, 279-280, 285, 288-292, 297, 300-301, 306-312, 315-321, 328-335, 340-351, 356, 359-360, 365, 368-371, 376-384, 387-393, 399-403 |
| coldfront/core/user/utils\_/merge\_users/runner.py                                                          |       93 |       66 |       20 |        0 |     24% |31-42, 46, 50, 55-56, 62-74, 80, 88-104, 109-143, 154-155, 160, 165-166, 172-176 |
| coldfront/core/user/views.py                                                                                |      461 |      166 |      124 |       20 |     59% |54-\>58, 76-82, 114, 116-\>119, 137-147, 218-229, 232-239, 249-262, 266, 383-384, 450-451, 456-461, 472, 475, 480, 483, 487, 492, 498-502, 517-521, 524-525, 529-530, 537, 550-551, 561-568, 571, 578, 581-602, 610-615, 654-657, 660-665, 706-715, 725-748, 751, 758-759, 776-784, 796-803, 809-837, 842-845, 850-862 |
| coldfront/core/user/views\_/link\_login\_views.py                                                           |       66 |        5 |        6 |        0 |     93% |     89-95 |
| coldfront/core/user/views\_/request\_hub\_views.py                                                          |      337 |       11 |       48 |        6 |     95% |76-77, 153-154, 160-161, 215-220, 795-\>802, 802-\>805, 805-\>808 |
| coldfront/core/utils/admin.py                                                                               |       46 |       17 |       12 |        0 |     50% |34-44, 51-56 |
| coldfront/core/utils/apps.py                                                                                |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/common.py                                                                              |       81 |        8 |       18 |        0 |     90% |31-32, 36, 50, 55-61 |
| coldfront/core/utils/context\_processors.py                                                                 |       55 |        3 |       14 |        0 |     96% |     66-70 |
| coldfront/core/utils/email/\_\_init\_\_.py                                                                  |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/email/email\_strategy.py                                                               |       40 |        7 |        6 |        1 |     83% |16, 26-27, 48-49, 69-70 |
| coldfront/core/utils/flag\_conditions.py                                                                    |       14 |        1 |        2 |        1 |     88% |        12 |
| coldfront/core/utils/forms/file\_upload\_forms.py                                                           |       14 |        1 |        2 |        1 |     88% |         9 |
| coldfront/core/utils/mail.py                                                                                |       47 |       11 |       20 |        6 |     72% |13-\>21, 25, 32-33, 35-\>38, 39, 42, 54-55, 85-90 |
| coldfront/core/utils/management/commands/add\_accounting\_defaults.py                                       |       30 |        0 |        6 |        0 |    100% |           |
| coldfront/core/utils/management/commands/add\_allowance\_defaults.py                                        |       50 |        0 |       16 |        0 |    100% |           |
| coldfront/core/utils/management/commands/add\_scheduled\_tasks.py                                           |       11 |       11 |        0 |        0 |      0% |      1-23 |
| coldfront/core/utils/management/commands/audit\_data.py                                                     |      117 |      117 |       60 |        0 |      0% |    20-427 |
| coldfront/core/utils/management/commands/create\_existing\_brc\_data.py                                     |      442 |      442 |      136 |        0 |      0% |     1-898 |
| coldfront/core/utils/management/commands/create\_staff\_group.py                                            |       18 |        3 |        6 |        2 |     79% |13, 32-\>39, 43-44 |
| coldfront/core/utils/management/commands/export\_data.py                                                    |      352 |       49 |      128 |       17 |     83% |312-313, 333, 344-\>343, 366-420, 446, 456, 487-\>exit, 572-\>exit, 613-614, 616-\>exit, 652-\>646, 670-\>675, 680, 685, 718, 729-730, 732-\>exit, 766-767, 772-\>775, 778-779, 795-796, 801-802 |
| coldfront/core/utils/management/commands/generate\_mou.py                                                   |       29 |        0 |        2 |        0 |    100% |           |
| coldfront/core/utils/management/commands/import\_grants.py                                                  |       60 |       60 |       16 |        0 |      0% |     1-189 |
| coldfront/core/utils/management/commands/import\_projects.py                                                |       63 |       63 |       16 |        0 |      0% |     1-157 |
| coldfront/core/utils/management/commands/import\_publications.py                                            |       30 |       30 |        4 |        0 |      0% |      1-86 |
| coldfront/core/utils/management/commands/import\_resources.py                                               |       71 |       71 |       32 |        0 |      0% |     1-160 |
| coldfront/core/utils/management/commands/import\_resources\_from\_json.py                                   |       87 |       87 |       30 |        0 |      0% |     1-151 |
| coldfront/core/utils/management/commands/import\_subscriptions.py                                           |       88 |       88 |       24 |        0 |      0% |     1-238 |
| coldfront/core/utils/management/commands/import\_users.py                                                   |       30 |       30 |       12 |        0 |      0% |      1-58 |
| coldfront/core/utils/management/commands/initial\_setup.py                                                  |       12 |       12 |        0 |        0 |      0% |      1-19 |
| coldfront/core/utils/management/commands/list\_latest\_project\_transactions.py                             |       14 |       14 |        2 |        0 |      0% |      1-22 |
| coldfront/core/utils/management/commands/load\_brc\_allocation\_data.py                                     |      167 |      167 |       46 |        0 |      0% |     1-483 |
| coldfront/core/utils/management/commands/load\_brc\_project\_descriptions.py                                |       67 |       67 |       14 |        0 |      0% |     1-137 |
| coldfront/core/utils/management/commands/load\_lrc\_data.py                                                 |      531 |      531 |      156 |        0 |      0% |    1-1115 |
| coldfront/core/utils/management/commands/load\_nodes.py                                                     |       30 |       30 |        8 |        0 |      0% |      1-45 |
| coldfront/core/utils/management/commands/load\_project\_transactions.py                                     |       38 |       38 |        8 |        0 |      0% |      1-59 |
| coldfront/core/utils/management/commands/load\_project\_user\_transactions.py                               |       52 |       52 |       14 |        0 |      0% |      1-89 |
| coldfront/core/utils/management/commands/load\_test\_data.py                                                |      124 |      124 |       12 |        0 |      0% |     1-754 |
| coldfront/core/utils/management/commands/set\_allocation\_end\_dates\_for\_periodic\_projects.py            |       41 |       41 |        8 |        0 |      0% |      1-65 |
| coldfront/core/utils/management/commands/set\_allocation\_start\_dates.py                                   |       46 |       46 |        8 |        0 |      0% |      1-62 |
| coldfront/core/utils/management/commands/set\_service\_unit\_usages\_from\_jobs.py                          |       66 |       66 |       14 |        0 |      0% |     1-115 |
| coldfront/core/utils/management/commands/show\_users\_in\_project\_but\_not\_in\_allocation.py              |       15 |       15 |        6 |        0 |      0% |      1-37 |
| coldfront/core/utils/management/commands/transform\_jobs.py                                                 |       65 |       65 |       18 |        0 |      0% |      1-95 |
| coldfront/core/utils/management/commands/update\_state\_and\_extra\_fields.py                               |       48 |       48 |       30 |        0 |      0% |     16-91 |
| coldfront/core/utils/management/commands/utils.py                                                           |       19 |       19 |        2 |        0 |      0% |      1-61 |
| coldfront/core/utils/management/commands/validate\_lrc\_initial\_state.py                                   |      200 |      200 |       76 |        0 |      0% |     1-398 |
| coldfront/core/utils/middleware.py                                                                          |       14 |        0 |        0 |        0 |    100% |           |
| coldfront/core/utils/mixins/views.py                                                                        |       67 |       26 |       18 |        2 |     55% |28-29, 45-49, 64-65, 80-90, 95-100, 105-115, 121-131 |
| coldfront/core/utils/mou.py                                                                                 |       90 |        5 |       26 |        4 |     91% |24-\>27, 52-\>56, 138-\>149, 169-177 |
| coldfront/core/utils/reporting/report\_message\_strategy.py                                                 |       51 |       51 |        2 |        0 |      0% |      1-83 |
| coldfront/core/utils/templatetags/common\_tags.py                                                           |       34 |       13 |       16 |        1 |     48% |38-43, 50-65, 75-\>exit |
| coldfront/core/utils/views/mou\_views.py                                                                    |      143 |       10 |       20 |        3 |     92% |62, 76, 142, 154, 212-213, 258-264 |
| coldfront/lib/brc\_mou\_generator/\_\_init\_\_.py                                                           |       60 |        4 |        0 |        0 |     93% |     59-67 |
| coldfront/plugins/departments/admin.py                                                                      |       32 |        8 |        4 |        0 |     67% |20, 31-34, 68, 71, 74 |
| coldfront/plugins/departments/apps.py                                                                       |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/conf/settings.py                                                              |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/forms.py                                                                      |       24 |        0 |        2 |        0 |    100% |           |
| coldfront/plugins/departments/management/commands/load\_departments.py                                      |       36 |       36 |       12 |        0 |      0% |      1-52 |
| coldfront/plugins/departments/management/commands/load\_user\_departments.py                                |       29 |       29 |        8 |        0 |      0% |      1-57 |
| coldfront/plugins/departments/models.py                                                                     |       17 |        1 |        0 |        0 |     94% |        21 |
| coldfront/plugins/departments/tasks.py                                                                      |        7 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/urls.py                                                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/utils/\_\_init\_\_.py                                                         |       13 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/departments/utils/data\_sources/\_\_init\_\_.py                                           |       13 |        2 |        0 |        0 |     85% |     21-22 |
| coldfront/plugins/departments/utils/data\_sources/backends/base.py                                          |        8 |        2 |        0 |        0 |     75% |    17, 40 |
| coldfront/plugins/departments/utils/data\_sources/backends/calnet\_ldap.py                                  |       79 |       79 |       32 |        0 |      0% |     1-252 |
| coldfront/plugins/departments/utils/data\_sources/backends/dummy.py                                         |       28 |        3 |       10 |        0 |     87% |     15-17 |
| coldfront/plugins/departments/utils/queries.py                                                              |       68 |        2 |       24 |        1 |     97% |     78-79 |
| coldfront/plugins/departments/views.py                                                                      |       35 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/admin.py                                                    |       15 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/api/permissions.py                                          |       15 |        1 |        8 |        1 |     91% |        27 |
| coldfront/plugins/faculty\_storage\_allocations/api/serializers.py                                          |       31 |        2 |        4 |        2 |     89% |    68, 94 |
| coldfront/plugins/faculty\_storage\_allocations/api/urls.py                                                 |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/api/views.py                                                |       41 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/apps.py                                                     |        6 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/conf/settings.py                                            |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/\_\_init\_\_.py                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/approval\_forms.py                                    |       28 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/form\_utils.py                                        |       41 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/forms/request\_forms.py                                     |       25 |        1 |        6 |        1 |     94% |        44 |
| coldfront/plugins/faculty\_storage\_allocations/management/commands/add\_faculty\_directory\_defaults.py    |       19 |        0 |        2 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/models.py                                                   |       57 |        1 |       10 |        0 |     99% |        39 |
| coldfront/plugins/faculty\_storage\_allocations/services/\_\_init\_\_.py                                    |        5 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/directory\_service.py                              |      132 |        6 |       28 |        1 |     96% |65, 149-151, 230, 418-419 |
| coldfront/plugins/faculty\_storage\_allocations/services/eligibility\_service.py                            |       15 |        0 |        6 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/notification\_service.py                           |       50 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/services/request\_service.py                                |      132 |        8 |       22 |        6 |     91% |190-\>192, 202, 250-251, 288-293, 317-\>323, 325, 332 |
| coldfront/plugins/faculty\_storage\_allocations/signals.py                                                  |       38 |        0 |        8 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/urls.py                                                     |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/utils/\_\_init\_\_.py                                       |       19 |        0 |        4 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/views/\_\_init\_\_.py                                       |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/faculty\_storage\_allocations/views/approval\_views.py                                    |      340 |       59 |       62 |       10 |     80% |60, 63-\>67, 133-\>142, 206-\>227, 208-225, 268-274, 287-350, 453, 455, 463-464, 473-476, 685-688, 769-772 |
| coldfront/plugins/faculty\_storage\_allocations/views/request\_views.py                                     |       83 |       18 |       12 |        3 |     78% |44, 60, 65-70, 81-82, 85-86, 89-91, 141-150 |
| coldfront/plugins/freeipa/\_\_init\_\_.py                                                                   |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/freeipa/apps.py                                                                           |        8 |        8 |        2 |        0 |      0% |      1-13 |
| coldfront/plugins/freeipa/management/commands/freeipa\_check.py                                             |      158 |      158 |       70 |        0 |      0% |     1-278 |
| coldfront/plugins/freeipa/management/commands/freeipa\_expire\_users.py                                     |       58 |       58 |       26 |        0 |      0% |     1-127 |
| coldfront/plugins/freeipa/search.py                                                                         |       46 |       46 |       10 |        0 |      0% |     1-100 |
| coldfront/plugins/freeipa/signals.py                                                                        |       17 |       17 |        0 |        0 |      0% |      1-30 |
| coldfront/plugins/freeipa/tasks.py                                                                          |       70 |       70 |       30 |        0 |      0% |     1-148 |
| coldfront/plugins/freeipa/utils.py                                                                          |       36 |       36 |        8 |        0 |      0% |      1-59 |
| coldfront/plugins/hardware\_procurements/conf/settings.py                                                   |        5 |        1 |        2 |        1 |     71% |         7 |
| coldfront/plugins/hardware\_procurements/forms.py                                                           |       18 |        5 |        0 |        0 |     72% |8, 46-47, 52-53 |
| coldfront/plugins/hardware\_procurements/management/commands/refresh\_hardware\_procurements\_cache.py      |       39 |       39 |        6 |        0 |      0% |      1-83 |
| coldfront/plugins/hardware\_procurements/urls.py                                                            |        3 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/\_\_init\_\_.py                                              |       57 |        1 |        8 |        1 |     97% |        62 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/\_\_init\_\_.py                                |       11 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/base.py                               |        5 |        1 |        0 |        0 |     80% |        12 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/cached.py                             |       97 |        4 |       42 |        1 |     96% |134-\>exit, 176-177, 186-187 |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/dummy.py                              |        4 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/hardware\_procurements/utils/data\_sources/backends/google\_sheets.py                     |       84 |        2 |       26 |        0 |     98% |     70-71 |
| coldfront/plugins/hardware\_procurements/views.py                                                           |      118 |       94 |       36 |        0 |     16% |26-28, 31-44, 49, 54-61, 64-66, 75-90, 101-102, 105-142, 145-146, 150-200 |
| coldfront/plugins/iquota/apps.py                                                                            |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/iquota/exceptions.py                                                                      |        7 |        7 |        0 |        0 |      0% |      1-17 |
| coldfront/plugins/iquota/urls.py                                                                            |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/iquota/utils.py                                                                           |       68 |       68 |       10 |        0 |      0% |     1-113 |
| coldfront/plugins/iquota/views.py                                                                           |       11 |       11 |        2 |        0 |      0% |      1-21 |
| coldfront/plugins/ldap\_user\_search/apps.py                                                                |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/ldap\_user\_search/utils.py                                                               |       37 |       37 |        6 |        0 |      0% |      1-71 |
| coldfront/plugins/mokey\_oidc/apps.py                                                                       |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/mokey\_oidc/auth.py                                                                       |       67 |       67 |       26 |        0 |      0% |     1-105 |
| coldfront/plugins/slurm/\_\_init\_\_.py                                                                     |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/slurm/apps.py                                                                             |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/slurm/associations.py                                                                     |      168 |      168 |       74 |        0 |      0% |     1-273 |
| coldfront/plugins/slurm/management/commands/slurm\_check.py                                                 |      189 |      189 |       80 |        0 |      0% |     1-357 |
| coldfront/plugins/slurm/management/commands/slurm\_dump.py                                                  |       37 |       37 |       16 |        0 |      0% |      1-54 |
| coldfront/plugins/slurm/utils.py                                                                            |       79 |       79 |       18 |        0 |      0% |     1-147 |
| coldfront/plugins/system\_monitor/utils.py                                                                  |       94 |       94 |       10 |        0 |      0% |     1-166 |
| coldfront/plugins/xdmod/\_\_init\_\_.py                                                                     |        1 |        0 |        0 |        0 |    100% |           |
| coldfront/plugins/xdmod/apps.py                                                                             |        3 |        3 |        0 |        0 |      0% |       1-5 |
| coldfront/plugins/xdmod/management/commands/xdmod\_usage.py                                                 |      147 |      147 |       72 |        0 |      0% |     1-347 |
| coldfront/plugins/xdmod/utils.py                                                                            |       84 |       84 |       12 |        0 |      0% |     1-135 |
| **TOTAL**                                                                                                   | **26411** | **10905** | **6206** |  **594** | **55%** |           |

101 empty files skipped.


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