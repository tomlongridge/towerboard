<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;
use App\Enums\SubscriptionType;

class CreateNotice extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('notices', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->timestamps();
            $table->string('title');
            $table->text('body');
            $table->date('expires')->nullable();
            $table->unsignedBigInteger('board_id'); // FK->boards
            $table->unsignedBigInteger('created_by');
            $table->unsignedTinyInteger('distribution')->default(SubscriptionType::BASIC);

            $table->softDeletes();
        });

    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('notices');
    }
}
